from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import List, Dict, Any
from datetime import datetime

from ..monitor import LogAnalyzer, AutoScaler, Config
from ..monitor.log_analyzer import LogEntry
from ..monitor.auto_scaler import ScalingDecision
from .models import (
    LogAnalysisRequest,
    LogAnalysisResponse,
    ScalingRequest,
    ScalingResponse,
    HealthResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize services
    config = Config.load_from_file()

    log_analyzer = LogAnalyzer(config)
    await log_analyzer.initialize()

    auto_scaler = AutoScaler(config=config)

    app.state.log_analyzer = log_analyzer
    app.state.auto_scaler = auto_scaler
    app.state.config = config

    yield

    # Cleanup
    await log_analyzer.close()


app = FastAPI(
    title="AI Service Monitor API",
    description="Intelligent service monitoring with LLM analysis and predictive scaling",
    version="0.1.0",
    lifespan=lifespan,
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
        status="healthy", timestamp=datetime.now().isoformat(), version="0.1.0"
    )


@app.post("/analyze/logs", response_model=LogAnalysisResponse)
async def analyze_logs(request: LogAnalysisRequest):
    try:
        log_analyzer = app.state.log_analyzer

        # Convert request logs to LogEntry objects
        log_entries = []
        for log_data in request.logs:
            log_entries.append(
                LogEntry(
                    timestamp=log_data.timestamp,
                    level=log_data.level,
                    service=log_data.service,
                    message=log_data.message,
                    metadata=log_data.metadata or {},
                )
            )

        # Analyze logs
        anomalies = await log_analyzer._analyze_log_batch(log_entries)

        return LogAnalysisResponse(
            anomalies=[
                {
                    "service": a.service,
                    "severity": a.severity,
                    "description": a.description,
                    "confidence": a.confidence,
                    "timestamp": a.timestamp.isoformat(),
                }
                for a in anomalies
            ]
        )

    except Exception as e:
        logger.error(f"Log analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scale/predict", response_model=ScalingResponse)
async def predict_scaling(request: ScalingRequest):
    try:
        auto_scaler = app.state.auto_scaler

        decision = await auto_scaler.predict_and_scale(request.service)

        if not decision:
            return ScalingResponse(
                service=request.service,
                action="none",
                reason="No scaling needed",
                confidence=0.0,
            )

        return ScalingResponse(
            service=decision.service,
            current_replicas=decision.current_replicas,
            target_replicas=decision.target_replicas,
            action=(
                "scale_up"
                if decision.target_replicas > decision.current_replicas
                else "scale_down"
            ),
            reason=decision.reason,
            confidence=decision.confidence,
        )

    except Exception as e:
        logger.error(f"Scaling prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/services/{service}/status")
async def get_service_status(service: str):
    try:
        auto_scaler = app.state.auto_scaler
        current_replicas = await auto_scaler._get_current_replicas(service)

        return {
            "service": service,
            "replicas": current_replicas,
            "status": (
                "running" if current_replicas and current_replicas > 0 else "stopped"
            ),
        }

    except Exception as e:
        logger.error(f"Failed to get service status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/services/{service}/scale")
async def manual_scale(
    service: str, target_replicas: int, background_tasks: BackgroundTasks
):
    try:
        auto_scaler = app.state.auto_scaler
        current_replicas = await auto_scaler._get_current_replicas(service)

        if not current_replicas:
            raise HTTPException(status_code=404, detail="Service not found")

        decision = ScalingDecision(
            service=service,
            current_replicas=current_replicas,
            target_replicas=target_replicas,
            reason="Manual scaling request",
            confidence=1.0,
            timestamp=datetime.now(),
        )

        background_tasks.add_task(auto_scaler._execute_scaling, decision)

        return {
            "service": service,
            "current_replicas": current_replicas,
            "target_replicas": target_replicas,
            "status": "scaling_initiated",
        }

    except Exception as e:
        logger.error(f"Manual scaling failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
