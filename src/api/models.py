from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    service: Optional[str] = None


class LogAnalysisRequest(BaseModel):
    logs: List[str]
    service: Optional[str] = None


class LogAnalysisResponse(BaseModel):
    status: str
    message: str
    anomalies: List[Dict[str, Any]] = []


class ScalingRequest(BaseModel):
    service: str
    target_replicas: Optional[int] = None


class ScalingResponse(BaseModel):
    service: str
    action: str
    reason: str
    confidence: float
    current_replicas: Optional[int] = None
    target_replicas: Optional[int] = None