from typing import Dict, Any, Optional
import yaml
import os
from pathlib import Path
from pydantic import BaseModel, Field


class ProjectConfig(BaseModel):
    name: str = "AI-log"
    gcp_project_id: str = "ai-log-468303"
    docker_registry: str = "gcr.io/ai-log-468303"
    namespace: str = "ai-monitor"


class LLMConfig(BaseModel):
    model: str = "llama3.2:3b"  # Ollama format by default
    max_tokens: int = 2048
    temperature: float = 0.1
    provider_type: str = "auto"  # auto, ollama, transformers, openai_compatible

    # Ollama specific
    ollama_url: str = "http://localhost:11434"

    # OpenAI Compatible API
    openai_base_url: str = "http://localhost:8080"
    api_key: str = "not-needed"

    # Mac M2 optimizations
    device: str = "auto"  # auto, mps, cpu
    use_metal: bool = True  # Apple Metal Performance Shaders


class ScalingConfig(BaseModel):
    prediction_window: str = "30m"
    scale_threshold: float = 0.8
    min_replicas: int = 2
    max_replicas: int = 20
    cooldown_period: str = "5m"


class MonitoringConfig(BaseModel):
    prometheus_url: str = "http://prometheus:9090"
    grafana_url: str = "http://grafana:3000"
    log_retention: str = "7d"


class KafkaConfig(BaseModel):
    bootstrap_servers: str = "kafka:9092"
    topics: Dict[str, str] = Field(
        default_factory=lambda: {
            "logs": "service-logs",
            "metrics": "service-metrics",
            "alerts": "service-alerts",
        }
    )


class RedisConfig(BaseModel):
    host: str = "redis"
    port: int = 6379
    db: int = 0


class Config(BaseModel):
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    scaling: ScalingConfig = Field(default_factory=ScalingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    kafka: KafkaConfig = Field(default_factory=KafkaConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)

    @classmethod
    def load_from_file(cls, config_path: Optional[str] = None) -> "Config":
        if config_path is None:
            config_path = os.getenv("CONFIG_PATH", "/app/config/monitor.yaml")

        config_file = Path(config_path)
        if not config_file.exists():
            return cls()

        with open(config_file, "r") as f:
            config_data = yaml.safe_load(f)

        return cls(**config_data)

    @classmethod
    def load_from_env(cls) -> "Config":
        config_data = {}

        if os.getenv("LLM_MODEL"):
            config_data.setdefault("llm", {})["model"] = os.getenv("LLM_MODEL")
        if os.getenv("MAX_TOKENS"):
            config_data.setdefault("llm", {})["max_tokens"] = int(
                os.getenv("MAX_TOKENS")
            )
        if os.getenv("TEMPERATURE"):
            config_data.setdefault("llm", {})["temperature"] = float(
                os.getenv("TEMPERATURE")
            )

        if os.getenv("PREDICTION_WINDOW"):
            config_data.setdefault("scaling", {})["prediction_window"] = os.getenv(
                "PREDICTION_WINDOW"
            )
        if os.getenv("SCALE_THRESHOLD"):
            config_data.setdefault("scaling", {})["scale_threshold"] = float(
                os.getenv("SCALE_THRESHOLD")
            )
        if os.getenv("MIN_REPLICAS"):
            config_data.setdefault("scaling", {})["min_replicas"] = int(
                os.getenv("MIN_REPLICAS")
            )
        if os.getenv("MAX_REPLICAS"):
            config_data.setdefault("scaling", {})["max_replicas"] = int(
                os.getenv("MAX_REPLICAS")
            )

        return cls(**config_data)
