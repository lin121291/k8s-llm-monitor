import asyncio
import logging
import platform
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
from abc import ABC, abstractmethod

from langchain.prompts import PromptTemplate
from langchain.llms.base import LLM
from langchain.schema import Generation, LLMResult
from langchain.callbacks.manager import CallbackManagerForLLMRun
import redis.asyncio as redis
from kafka import KafkaConsumer, KafkaProducer
import pandas as pd
import numpy as np
import httpx

from .config import Config


@dataclass
class LogEntry:
    timestamp: datetime
    level: str
    service: str
    message: str
    metadata: Dict[str, Any]


@dataclass
class Anomaly:
    timestamp: datetime
    service: str
    severity: str
    description: str
    confidence: float
    context: Dict[str, Any]


class BaseLLMProvider(ABC):
    """Base class for LLM providers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate response from LLM"""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the LLM provider is available"""
        pass


class OllamaProvider(BaseLLMProvider):
    """Ollama Provider for Mac M2 and local deployment"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("ollama_url", "http://localhost:11434")
        self.model = config.get("model", "llama3.2:3b")
        self.client = httpx.AsyncClient(timeout=60.0)

    async def is_available(self) -> bool:
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return any(
                    model["name"].startswith(self.model.split(":")[0])
                    for model in models
                )
            return False
        except Exception:
            return False

    async def generate(self, prompt: str) -> str:
        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.config.get("temperature", 0.1),
                        "num_predict": self.config.get("max_tokens", 2048),
                    },
                },
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                raise Exception(f"Ollama API error: {response.status_code}")

        except Exception as e:
            self.logger.error(f"Ollama generation failed: {e}")
            raise


class TransformersProvider(BaseLLMProvider):
    """Hugging Face Transformers Provider with Mac M2 MPS support"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_name = config.get("model", "microsoft/DialoGPT-small")
        self.device = self._get_best_device()
        self._pipeline = None

    def _get_best_device(self) -> str:
        try:
            import torch

            if torch.backends.mps.is_available():
                return "mps"
            elif torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    async def is_available(self) -> bool:
        try:
            import torch
            import transformers

            return True
        except ImportError:
            return False

    async def generate(self, prompt: str) -> str:
        try:
            if self._pipeline is None:
                from transformers import pipeline

                self._pipeline = pipeline(
                    "text-generation",
                    model=self.model_name,
                    device=self.device,
                    torch_dtype="auto",
                )

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._pipeline(
                    prompt,
                    max_length=self.config.get("max_tokens", 512),
                    temperature=self.config.get("temperature", 0.1),
                    do_sample=True,
                    pad_token_id=self._pipeline.tokenizer.eos_token_id,
                ),
            )

            return result[0]["generated_text"][len(prompt) :].strip()

        except Exception as e:
            self.logger.error(f"Transformers generation failed: {e}")
            raise


class AdaptiveLLM(LLM):
    """Adaptive LLM that automatically selects the best provider based on platform"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        object.__setattr__(self, "config", config)
        object.__setattr__(self, "_provider", None)
        object.__setattr__(self, "_initialized", False)

    async def _ensure_provider(self):
        if not self._initialized:
            provider_type = self.config.get("provider_type", "auto")

            if provider_type == "auto":
                provider_type = self._detect_best_provider()

            providers = {"ollama": OllamaProvider, "transformers": TransformersProvider}

            provider_class = providers.get(provider_type)
            if provider_class:
                self._provider = provider_class(self.config)
                if not await self._provider.is_available():
                    # Fallback to transformers
                    self._provider = TransformersProvider(self.config)
            else:
                self._provider = TransformersProvider(self.config)

            self._initialized = True

    def _detect_best_provider(self) -> str:
        """Automatically detect the best provider"""
        system = platform.system().lower()
        machine = platform.machine().lower()

        if system == "darwin" and "arm64" in machine:
            return "ollama"

        return "transformers"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        return asyncio.run(self.acall(prompt, stop, run_manager, **kwargs))

    async def acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        await self._ensure_provider()
        return await self._provider.generate(prompt)

    @property
    def _llm_type(self) -> str:
        return "adaptive_llm"


class LogAnalyzer:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.load_from_env()
        self.logger = logging.getLogger(__name__)

        # Use adaptive LLM that automatically selects the best provider for Mac M2
        llm_config = {
            "provider_type": getattr(self.config.llm, "provider_type", "auto"),
            "model": self.config.llm.model,
            "max_tokens": self.config.llm.max_tokens,
            "temperature": self.config.llm.temperature,
            "ollama_url": getattr(
                self.config.llm, "ollama_url", "http://localhost:11434"
            ),
            "openai_base_url": getattr(
                self.config.llm, "openai_base_url", "http://localhost:8080"
            ),
            "api_key": getattr(self.config.llm, "api_key", "not-needed"),
        }

        self.llm = AdaptiveLLM(llm_config)

        self.redis_client = None
        self.kafka_consumer = None
        self.kafka_producer = None

        self.anomaly_prompt = PromptTemplate(
            input_variables=["logs", "context"],
            template="""
            Analyze the following service logs for anomalies and potential issues.
            
            Context: {context}
            
            Logs:
            {logs}
            
            Identify:
            1. Any error patterns or unusual behavior
            2. Performance degradation indicators  
            3. Security-related concerns
            4. Resource utilization issues
            
            Return analysis as JSON with fields: severity (low/medium/high/critical), 
            description, confidence (0-1), and recommendations.
            """,
        )

    async def initialize(self) -> None:
        self.redis_client = redis.from_url(
            f"redis://{self.config.redis.host}:{self.config.redis.port}/{self.config.redis.db}"
        )

        self.kafka_consumer = KafkaConsumer(
            self.config.kafka.topics["logs"],
            bootstrap_servers=[self.config.kafka.bootstrap_servers],
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        )

        self.kafka_producer = KafkaProducer(
            bootstrap_servers=[self.config.kafka.bootstrap_servers],
            value_serializer=lambda x: json.dumps(x).encode("utf-8"),
        )

    async def detect_anomalies(
        self, log_stream: AsyncGenerator[LogEntry, None]
    ) -> AsyncGenerator[Anomaly, None]:
        log_buffer = []
        buffer_size = 100

        async for log_entry in log_stream:
            log_buffer.append(log_entry)

            if len(log_buffer) >= buffer_size:
                anomalies = await self._analyze_log_batch(log_buffer)
                for anomaly in anomalies:
                    yield anomaly

                log_buffer = log_buffer[-10:]

    async def _analyze_log_batch(self, logs: List[LogEntry]) -> List[Anomaly]:
        log_text = self._format_logs_for_analysis(logs)
        context = await self._get_service_context(logs)

        try:
            prompt = self.anomaly_prompt.format(logs=log_text, context=context)
            response_text = await self.llm.acall(prompt)

            try:
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                analysis = self._parse_llm_response(response_text)

            return [
                Anomaly(
                    timestamp=datetime.now(),
                    service=self._extract_primary_service(logs),
                    severity=analysis.get("severity", "low"),
                    description=analysis.get("description", "No description"),
                    confidence=analysis.get("confidence", 0.5),
                    context=analysis.get("recommendations", {}),
                )
            ]
        except Exception as e:
            self.logger.error(f"Error analyzing logs: {e}")
            return []

    def _format_logs_for_analysis(self, logs: List[LogEntry]) -> str:
        formatted = []
        for log in logs[-20:]:  # Last 20 logs for context
            formatted.append(
                f"[{log.timestamp}] {log.level} {log.service}: {log.message}"
            )
        return "\n".join(formatted)

    async def _get_service_context(self, logs: List[LogEntry]) -> str:
        services = set(log.service for log in logs)
        context_data = []

        for service in services:
            try:
                cached_context = await self.redis_client.get(f"context:{service}")
                if cached_context:
                    context_data.append(cached_context.decode())
            except Exception:
                pass

        return "; ".join(context_data) if context_data else "No additional context"

    def _extract_primary_service(self, logs: List[LogEntry]) -> str:
        service_counts = {}
        for log in logs:
            service_counts[log.service] = service_counts.get(log.service, 0) + 1

        return (
            max(service_counts, key=service_counts.get) if service_counts else "unknown"
        )

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response when it's not pure JSON"""
        # Simple text parsing to extract key information
        analysis = {
            "severity": "medium",
            "description": "LLM analysis completed",
            "confidence": 0.5,
            "recommendations": {},
        }

        response_lower = response_text.lower()

        if any(word in response_lower for word in ["critical", "severe", "urgent"]):
            analysis["severity"] = "critical"
            analysis["confidence"] = 0.8
        elif any(
            word in response_lower for word in ["high", "important", "significant"]
        ):
            analysis["severity"] = "high"
            analysis["confidence"] = 0.7
        elif any(word in response_lower for word in ["low", "minor"]):
            analysis["severity"] = "low"
            analysis["confidence"] = 0.4

        analysis["description"] = response_text[:200].strip()

        return analysis

    async def publish_anomaly(self, anomaly: Anomaly) -> None:
        anomaly_data = {
            "timestamp": anomaly.timestamp.isoformat(),
            "service": anomaly.service,
            "severity": anomaly.severity,
            "description": anomaly.description,
            "confidence": anomaly.confidence,
            "context": anomaly.context,
        }

        try:
            self.kafka_producer.send(
                self.config.kafka.topics["alerts"], value=anomaly_data
            )

            await self.redis_client.setex(
                f"anomaly:{anomaly.service}:{anomaly.timestamp.isoformat()}",
                3600,  # 1 hour expiration
                json.dumps(anomaly_data),
            )

        except Exception as e:
            self.logger.error(f"Failed to publish anomaly: {e}")

    async def close(self) -> None:
        if self.redis_client:
            await self.redis_client.close()
        if self.kafka_consumer:
            self.kafka_consumer.close()
        if self.kafka_producer:
            self.kafka_producer.close()
