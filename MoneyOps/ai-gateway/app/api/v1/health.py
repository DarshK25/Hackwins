"""
Health check endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import time

from app.config import settings
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Track startup time
startup_time = time.time()


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    version: str
    environment: str
    uptime_seconds: float
    checks: Dict[str, Any]

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint
    Returns service health and version info
    """
    uptime = time.time() - startup_time
    
    # Perform health checks
    checks = {
        "api": "healthy",
        # TODO: Add more checks (Redis, Backend, etc.)
    }
    
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        uptime_seconds=round(uptime, 2),
        checks=checks,
    )


@router.get("/health/ready")
async def readiness_check():
    """
    Kubernetes readiness probe
    Checks if service can accept traffic
    """
    # TODO: Check dependencies (Redis, Backend API)
    
    checks = {
        "api": True,
        # "redis": await check_redis(),
        # "backend": await check_backend(),
    }
    
    all_healthy = all(checks.values())
    
    if not all_healthy:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return {"status": "ready", "checks": checks}


@router.get("/health/live")
async def liveness_check():
    """
    Kubernetes liveness probe
    Simple check that process is alive
    """
    return {"status": "alive"}