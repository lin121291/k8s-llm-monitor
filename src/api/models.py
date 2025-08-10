from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class LogEntryModel(BaseModel):
    timestamp: datetime
    level: str = Field(..., pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    service: str
    message: str
    metadata: Optional[Dict[str, Any]] = None


class LogAnalysisRequest(BaseModel):
    logs: List[LogEntryModel]
    context: Optional[str] = None


class AnomalyModel(BaseModel):
    service: str
    severity: str
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    timestamp: str


class LogAnalysisResponse(BaseModel):
    anomalies: List[AnomalyModel]


class ScalingRequest(BaseModel):
    service: str
    force: bool = False


class ScalingResponse(BaseModel):
    service: str
    current_replicas: Optional[int] = None
    target_replicas: Optional[int] = None
    action: str  # "scale_up", "scale_down", "none"
    reason: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str


class ServiceStatusResponse(BaseModel):
    service: str
    replicas: int
    status: str  # "running", "stopped", "scaling"
    last_scaled: Optional[str] = None


class MetricModel(BaseModel):
    timestamp: datetime
    service: str
    metric_name: str
    value: float
    labels: Optional[Dict[str, str]] = None


class MetricsRequest(BaseModel):
    service: str
    start_time: datetime
    end_time: datetime
    metrics: List[str]  # ["cpu_usage", "memory_usage", "request_rate"]


class MetricsResponse(BaseModel):
    service: str
    metrics: List[MetricModel]
