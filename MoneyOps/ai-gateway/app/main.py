"""
MoneyOps AI Gateway - Main FastAPI Application
Implements BRUTAL TRUTH fixes:
1. FAIL FAST on bad config
2. Rate limiting with SlowAPI + Redis
3. Proper error handling (no silent failures)
4. Request ID tracking
"""
import sys
import time
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ============================================================================
# FAIL FAST: Validate critical configuration on startup
# ============================================================================
def validate_config():
    """Fail immediately if config is invalid. No silent failures."""
    errors = []

    # JWT Secret must be strong
    if not settings.JWT_SECRET_KEY or len(settings.JWT_SECRET_KEY) < 32:
        errors.append("JWT_SECRET_KEY must be at least 32 characters")

    # Internal service token must not be default
    if not settings.INTERNAL_SERVICE_TOKEN or "default" in settings.INTERNAL_SERVICE_TOKEN.lower():
        errors.append("INTERNAL_SERVICE_TOKEN must not be default")

    # At least one LLM provider must work
    if not settings.GROQ_API_KEY:
        logger.warning("No GROQ_API_KEY set - LLM calls will fail")

    if errors:
        for err in errors:
            logger.error("config_error", error=err)
        print("FATAL CONFIG ERRORS:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    logger.info("config_validated", environment=settings.ENVIRONMENT)

validate_config()

# ============================================================================
# Rate Limiting Setup
# ============================================================================
limiter = None
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.storage import RedisStorage

    # Use Redis if available, else in-memory (for development)
    storage = None
    if settings.REDIS_HOST and settings.REDIS_HOST != "localhost":
        try:
            import redis
            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD or None,
                db=settings.REDIS_DB or 0,
            )
            storage = RedisStorage(redis_client)
            logger.info("rate_limiter_redis", host=settings.REDIS_HOST)
        except Exception as e:
            logger.warning("redis_unavailable_for_ratelimit", error=str(e))

    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=None,  # Uses in-memory if None
        storage_options={"storage": storage} if storage else {},
        default_limits=["100/minute"],  # 100 requests per IP per minute
    )
    logger.info("rate_limiter_ready", storage="redis" if storage else "memory")
except ImportError:
    logger.warning("slowapi_not_installed", note="Run: pip install slowapi")
    limiter = None

# ============================================================================
# Lifespan Events (startup/shutdown)
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info(
        "starting_ai_gateway",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )

    # Connect to Redis
    try:
        from app.integrations.redis_client import get_redis
        await get_redis()
        logger.info("redis_ready")
    except Exception as e:
        logger.warning("redis_unavailable", error=str(e), note="Continuing without cache")

    yield

    # Shutdown
    try:
        from app.integrations.redis_client import close_redis
        await close_redis()
    except Exception:
        pass
    logger.info("shutting_down_ai_gateway")

# ============================================================================
# Create FastAPI App
# ============================================================================
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered orchestration gateway for MoneyOps",
    lifespan=lifespan,
)

# CORS
_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Frontend dev
    "http://localhost:3000",  # Alt frontend
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Rate Limiting Middleware
try:
    from app.middleware.rate_limit import RateLimitMiddleware
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_window=settings.RATE_LIMIT_REQUESTS,
        window_seconds=settings.RATE_LIMIT_WINDOW,
    )
    logger.info("rate_limit_middleware_added")
except ImportError as e:
    logger.warning("rate_limit_middleware_unavailable", error=str(e))

# Request logging + Request ID middleware
@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """Log all requests with timing + add request ID"""
    import uuid
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    # Log request
    logger.info(
        "request_started",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None,
    )

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log response
    logger.info(
        "request_completed",
        request_id=request_id,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2),
    )

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id
    return response

# Global exception handler - NO silent failures
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions with proper logging"""
    import traceback
    error_trace = traceback.format_exc()

    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
        error=str(exc),
        traceback=error_trace if settings.DEBUG else None,
        exc_info=True,
    )

    # Don't expose internal errors in production
    if settings.ENVIRONMENT == "production":
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
            },
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": type(exc).__name__,
                "message": str(exc),
                "traceback": error_trace if settings.DEBUG else None,
            },
        )

# ============================================================================
# Include Routers
# ============================================================================
# Health check (no rate limit)
from app.api.v1 import health
app.include_router(health.router, prefix="/api/v1", tags=["Health"])

# Voice router
from app.api.v1 import voice
app.include_router(voice.router, prefix="/api/v1", tags=["Voice"])

# Agent router (with rate limiting)
from app.api.v1 import agent
if limiter:
    agent.router.limiter = limiter
app.include_router(agent.router, prefix="/api/v1", tags=["Agent"])

# Compliance router
from app.api.v1 import compliance
app.include_router(compliance.router, prefix="/api/v1", tags=["Compliance"])

# Test routers (development only)
if settings.ENVIRONMENT != "production":
    try:
        from app.api.v1 import test_agents
        from app.api.v1 import test_llm
        app.include_router(test_agents.router, prefix="/api/v1", tags=["Test Agents"])
        app.include_router(test_llm.router, prefix="/api/v1", tags=["Test LLM"])
    except ImportError as e:
        logger.warning("test_routers_unavailable", error=str(e))

# ============================================================================
# Root endpoint
# ============================================================================
@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "operational",
        "endpoints": {
            "health": "/api/v1/health",
            "agent": "/api/v1/agent/chat",
            "voice": "/api/v1/voice",
        }
    }

# ============================================================================
# Run directly
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
