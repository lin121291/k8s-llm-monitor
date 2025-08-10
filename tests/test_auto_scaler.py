import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.monitor.auto_scaler import AutoScaler, MetricData, ScalingDecision
from src.monitor.config import Config


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def auto_scaler(config):
    with patch("src.monitor.auto_scaler.k8s_config"):
        return AutoScaler(cluster="test", config=config)


@pytest.fixture
def sample_metrics():
    return [
        MetricData(
            timestamp=datetime.now(),
            service="api-gateway",
            cpu_usage=0.6,
            memory_usage=0.7,
            request_rate=100.0,
            response_time=0.2,
        ),
        MetricData(
            timestamp=datetime.now(),
            service="api-gateway",
            cpu_usage=0.8,
            memory_usage=0.75,
            request_rate=150.0,
            response_time=0.3,
        ),
    ]


class TestAutoScaler:
    def test_initialization(self, auto_scaler):
        assert auto_scaler.cluster == "test"
        assert auto_scaler.config is not None
        assert auto_scaler.prediction_models == {}
        assert auto_scaler.metric_history == {}

    @pytest.mark.asyncio
    async def test_collect_metrics_success(self, auto_scaler):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "result": [{"values": [[1234567890, "100.5"], [1234567950, "120.3"]]}]
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            metrics = await auto_scaler._collect_metrics("test-service")

            assert metrics is not None
            assert len(metrics) == 2
            assert metrics[0].request_rate == 100.5
            assert metrics[1].request_rate == 120.3

    def test_parse_prometheus_data(self, auto_scaler):
        data = {
            "data": {
                "result": [{"values": [[1234567890, "50.0"], [1234567950, "75.0"]]}]
            }
        }

        metrics = auto_scaler._parse_prometheus_data("test-service", data)

        assert len(metrics) == 2
        assert metrics[0].service == "test-service"
        assert metrics[0].request_rate == 50.0
        assert metrics[1].request_rate == 75.0

    @pytest.mark.asyncio
    async def test_predict_load_with_insufficient_data(
        self, auto_scaler, sample_metrics
    ):
        # Test with insufficient historical data
        prediction = await auto_scaler._predict_load("test-service", sample_metrics[:1])

        assert prediction == sample_metrics[0].request_rate

    @pytest.mark.asyncio
    async def test_predict_load_with_sufficient_data(self, auto_scaler, sample_metrics):
        # Populate some historical data
        auto_scaler.metric_history["test-service"] = (
            sample_metrics * 5
        )  # 10 data points

        prediction = await auto_scaler._predict_load("test-service", sample_metrics)

        assert isinstance(prediction, float)
        assert prediction >= 0  # Should be non-negative

    def test_calculate_target_replicas_scale_up(self, auto_scaler):
        # High load should trigger scale up
        target = auto_scaler._calculate_target_replicas("test-service", 1.0, 3)

        assert target > 3  # Should scale up
        assert target <= auto_scaler.config.scaling.max_replicas

    def test_calculate_target_replicas_scale_down(self, auto_scaler):
        # Low load should maintain current replicas
        target = auto_scaler._calculate_target_replicas("test-service", 0.3, 3)

        assert target == 3  # Should maintain current replicas

    def test_calculate_target_replicas_limits(self, auto_scaler):
        # Test minimum limit
        target_min = auto_scaler._calculate_target_replicas("test-service", 0.1, 1)
        assert target_min >= auto_scaler.config.scaling.min_replicas

        # Test maximum limit
        target_max = auto_scaler._calculate_target_replicas("test-service", 10.0, 5)
        assert target_max <= auto_scaler.config.scaling.max_replicas

    def test_calculate_confidence(self, auto_scaler, sample_metrics):
        confidence = auto_scaler._calculate_confidence("test-service", sample_metrics)

        assert 0.1 <= confidence <= 0.9
        assert isinstance(confidence, float)

    @pytest.mark.asyncio
    async def test_get_current_replicas(self, auto_scaler):
        mock_deployment = Mock()
        mock_deployment.status.replicas = 3

        with patch.object(
            auto_scaler.k8s_apps_v1,
            "read_namespaced_deployment",
            return_value=mock_deployment,
        ):
            replicas = await auto_scaler._get_current_replicas("test-service")

            assert replicas == 3

    @pytest.mark.asyncio
    async def test_should_scale_high_confidence(self, auto_scaler):
        decision = ScalingDecision(
            service="test-service",
            current_replicas=2,
            target_replicas=4,
            reason="High load predicted",
            confidence=0.8,
            timestamp=datetime.now(),
        )

        should_scale = await auto_scaler._should_scale(decision)
        assert should_scale is True

    @pytest.mark.asyncio
    async def test_should_scale_low_confidence(self, auto_scaler):
        decision = ScalingDecision(
            service="test-service",
            current_replicas=2,
            target_replicas=4,
            reason="Uncertain prediction",
            confidence=0.3,
            timestamp=datetime.now(),
        )

        should_scale = await auto_scaler._should_scale(decision)
        assert should_scale is False

    @pytest.mark.asyncio
    async def test_execute_scaling_success(self, auto_scaler):
        decision = ScalingDecision(
            service="test-service",
            current_replicas=2,
            target_replicas=4,
            reason="Scale up",
            confidence=0.8,
            timestamp=datetime.now(),
        )

        with patch.object(
            auto_scaler.k8s_apps_v1, "patch_namespaced_deployment_scale"
        ) as mock_patch:
            result = await auto_scaler._execute_scaling(decision)

            assert result is True
            mock_patch.assert_called_once()


class TestMetricData:
    def test_metric_data_creation(self):
        metric = MetricData(
            timestamp=datetime.now(),
            service="test-service",
            cpu_usage=0.5,
            memory_usage=0.6,
            request_rate=100.0,
            response_time=0.2,
        )

        assert metric.service == "test-service"
        assert metric.cpu_usage == 0.5
        assert metric.request_rate == 100.0


class TestScalingDecision:
    def test_scaling_decision_creation(self):
        decision = ScalingDecision(
            service="test-service",
            current_replicas=2,
            target_replicas=4,
            reason="High load",
            confidence=0.8,
            timestamp=datetime.now(),
        )

        assert decision.service == "test-service"
        assert decision.current_replicas == 2
        assert decision.target_replicas == 4
        assert decision.confidence == 0.8
