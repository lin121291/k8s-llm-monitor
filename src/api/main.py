from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

from .models import HealthResponse, LogAnalysisRequest, LogAnalysisResponse, ScalingRequest, ScalingResponse

app = FastAPI(
    title="AI Service Monitor API",
    description="Intelligent service monitoring with LLM analysis and predictive scaling",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="0.1.0",
        service="api-gateway"
    )


@app.get("/health/detailed")
async def detailed_health_check():
    return {
        "api": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0",
        "overall_status": "healthy"
    }


@app.post("/analyze/logs", response_model=LogAnalysisResponse)
async def analyze_logs(request: LogAnalysisRequest):
    return LogAnalysisResponse(
        status="ok",
        message=f"Analyzed {len(request.logs)} logs for service {request.service or 'unknown'}",
        anomalies=[]
    )


@app.post("/scale/predict", response_model=ScalingResponse)
async def predict_scaling(request: ScalingRequest):
    return ScalingResponse(
        service=request.service,
        action="none",
        reason="No scaling needed (simplified for demo)",
        confidence=0.8,
        current_replicas=2,
        target_replicas=request.target_replicas or 2
    )


@app.get("/services/{service}/status")
async def get_service_status(service: str):
    return {
        "service": service,
        "replicas": 2,
        "status": "running"
    }


@app.post("/services/{service}/scale")
async def manual_scale(service: str, target_replicas: int = 2):
    return {
        "service": service,
        "current_replicas": 2,
        "target_replicas": target_replicas,
        "status": "scaling_initiated"
    }


@app.get("/services")
async def list_monitored_services():
    return {
        "services": [
            {
                "name": "sample-service",
                "current_replicas": 2,
                "last_scaling": None,
                "metrics_count": 0
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)