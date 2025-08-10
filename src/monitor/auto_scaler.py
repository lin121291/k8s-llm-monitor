import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from kubernetes import client, config as k8s_config
from prometheus_client.parser import text_string_to_metric_families
import httpx

from .config import Config


@dataclass
class MetricData:
    timestamp: datetime
    service: str
    cpu_usage: float
    memory_usage: float
    request_rate: float
    response_time: float


@dataclass
class ScalingDecision:
    service: str
    current_replicas: int
    target_replicas: int
    reason: str
    confidence: float
    timestamp: datetime


class AutoScaler:
    def __init__(self, cluster: str = "production", config: Optional[Config] = None):
        self.cluster = cluster
        self.config = config or Config.load_from_env()
        self.logger = logging.getLogger(__name__)

        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            k8s_config.load_kube_config()

        self.k8s_apps_v1 = client.AppsV1Api()
        self.k8s_autoscaling_v1 = client.AutoscalingV1Api()

        self.prediction_models: Dict[str, Tuple[LinearRegression, StandardScaler]] = {}
        self.metric_history: Dict[str, List[MetricData]] = {}

    async def predict_and_scale(self, service: str) -> Optional[ScalingDecision]:
        metrics = await self._collect_metrics(service)
        if not metrics:
            self.logger.warning(f"No metrics available for service: {service}")
            return None

        prediction = await self._predict_load(service, metrics)
        current_replicas = await self._get_current_replicas(service)

        if current_replicas is None:
            return None

        target_replicas = self._calculate_target_replicas(
            service, prediction, current_replicas
        )

        if target_replicas != current_replicas:
            scaling_decision = ScalingDecision(
                service=service,
                current_replicas=current_replicas,
                target_replicas=target_replicas,
                reason=f"Predicted load: {prediction:.2f}",
                confidence=self._calculate_confidence(service, metrics),
                timestamp=datetime.now(),
            )

            if await self._should_scale(scaling_decision):
                await self._execute_scaling(scaling_decision)
                return scaling_decision

        return None

    async def _collect_metrics(self, service: str) -> Optional[List[MetricData]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.monitoring.prometheus_url}/api/v1/query_range",
                    params={
                        "query": f'rate(http_requests_total{{service="{service}"}}[5m])',
                        "start": (datetime.now() - timedelta(hours=1)).isoformat(),
                        "end": datetime.now().isoformat(),
                        "step": "60s",
                    },
                )

                if response.status_code != 200:
                    return None

                data = response.json()
                return self._parse_prometheus_data(service, data)

        except Exception as e:
            self.logger.error(f"Failed to collect metrics for {service}: {e}")
            return None

    def _parse_prometheus_data(self, service: str, data: Dict) -> List[MetricData]:
        metrics = []

        if "data" in data and "result" in data["data"]:
            for result in data["data"]["result"]:
                for timestamp, value in result.get("values", []):
                    metrics.append(
                        MetricData(
                            timestamp=datetime.fromtimestamp(float(timestamp)),
                            service=service,
                            cpu_usage=0.0,  # Would be fetched from separate query
                            memory_usage=0.0,  # Would be fetched from separate query
                            request_rate=float(value),
                            response_time=0.0,  # Would be fetched from separate query
                        )
                    )

        return metrics

    async def _predict_load(self, service: str, metrics: List[MetricData]) -> float:
        if service not in self.metric_history:
            self.metric_history[service] = []

        self.metric_history[service].extend(metrics)

        # Keep only last 1000 data points
        self.metric_history[service] = self.metric_history[service][-1000:]

        if len(self.metric_history[service]) < 10:
            return metrics[-1].request_rate if metrics else 0.0

        # Prepare training data
        df = pd.DataFrame(
            [
                {
                    "timestamp": m.timestamp.timestamp(),
                    "request_rate": m.request_rate,
                    "cpu_usage": m.cpu_usage,
                    "memory_usage": m.memory_usage,
                }
                for m in self.metric_history[service]
            ]
        )

        # Create features (time-based features)
        df["hour"] = pd.to_datetime(df["timestamp"], unit="s").dt.hour
        df["day_of_week"] = pd.to_datetime(df["timestamp"], unit="s").dt.dayofweek

        # Simple prediction based on recent trend
        recent_data = df.tail(30)  # Last 30 data points
        if len(recent_data) < 5:
            return df["request_rate"].iloc[-1]

        # Linear regression on recent data
        X = np.arange(len(recent_data)).reshape(-1, 1)
        y = recent_data["request_rate"].values

        try:
            model = LinearRegression()
            model.fit(X, y)

            # Predict next value
            prediction = model.predict([[len(recent_data)]])[0]
            return max(0, prediction)  # Ensure non-negative

        except Exception as e:
            self.logger.error(f"Prediction failed for {service}: {e}")
            return df["request_rate"].iloc[-1]

    async def _get_current_replicas(self, service: str) -> Optional[int]:
        try:
            deployment = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.k8s_apps_v1.read_namespaced_deployment(
                    name=service, namespace="ai-monitor"
                ),
            )
            return deployment.status.replicas
        except Exception as e:
            self.logger.error(f"Failed to get current replicas for {service}: {e}")
            return None

    def _calculate_target_replicas(
        self, service: str, predicted_load: float, current_replicas: int
    ) -> int:
        # Simple scaling logic based on predicted load
        # This would be more sophisticated in production

        if predicted_load > self.config.scaling.scale_threshold:
            scale_factor = predicted_load / self.config.scaling.scale_threshold
            target = max(current_replicas + 1, int(current_replicas * scale_factor))
        else:
            target = current_replicas

        # Apply limits
        target = max(self.config.scaling.min_replicas, target)
        target = min(self.config.scaling.max_replicas, target)

        return target

    def _calculate_confidence(self, service: str, metrics: List[MetricData]) -> float:
        if len(metrics) < 5:
            return 0.3

        # Calculate confidence based on data consistency
        request_rates = [m.request_rate for m in metrics[-10:]]
        variance = np.var(request_rates)

        # Lower variance = higher confidence
        confidence = max(0.1, min(0.9, 1.0 / (1.0 + variance)))

        return confidence

    async def _should_scale(self, decision: ScalingDecision) -> bool:
        # Check cooldown period
        cooldown_key = f"cooldown:{decision.service}"

        # In a real implementation, you'd check Redis or similar storage
        # for last scaling time

        return decision.confidence > 0.5

    async def _execute_scaling(self, decision: ScalingDecision) -> bool:
        try:
            body = {"spec": {"replicas": decision.target_replicas}}

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.k8s_apps_v1.patch_namespaced_deployment_scale(
                    name=decision.service, namespace="ai-monitor", body=body
                ),
            )

            self.logger.info(
                f"Scaled {decision.service} from {decision.current_replicas} "
                f"to {decision.target_replicas} replicas"
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to scale {decision.service}: {e}")
            return False

    async def monitor_and_scale(self, services: List[str]) -> None:
        while True:
            for service in services:
                try:
                    decision = await self.predict_and_scale(service)
                    if decision:
                        self.logger.info(f"Scaling decision: {decision}")
                except Exception as e:
                    self.logger.error(f"Error processing {service}: {e}")

            await asyncio.sleep(60)  # Check every minute
