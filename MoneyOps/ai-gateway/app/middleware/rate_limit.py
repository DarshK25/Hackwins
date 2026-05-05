"""
Rate limiting middleware for FastAPI.
Uses Redis to track request counts per client/IP.
"""
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window algorithm with Redis.

    Uses Redis to track request counts per client across multiple workers.
    Falls back to in-memory tracking if Redis is unavailable.
    """

    def __init__(
        self,
        app: ASGIApp,
        requests_per_window: int = None,
        window_seconds: int = None,
    ):
        super().__init__(app)
        self.requests_per_window = requests_per_window or settings.RATE_LIMIT_REQUESTS
        self.window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW

        self._use_redis = False
        self._in_memory_store: Dict[str, list] = {}  # client_id -> list of timestamps

        # Try to connect to Redis
        try:
            from app.integrations.redis_client import get_redis
            self._use_redis = True
            self._redis_get = get_redis
            logger.info(
                "rate_limit_redis_enabled",
                requests=self.requests_per_window,
                window=self.window_seconds,
            )
        except ImportError:
            logger.warning("rate_limit_redis_unavailable_using_in_memory")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and internal endpoints
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get client identifier (user_id from headers, or IP address)
        client_id = self._get_client_id(request)
        if not client_id:
            return await call_next(request)

        # Check rate limit
        allowed, retry_after = await self._check_rate_limit(client_id)

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": retry_after,
                    "limit": self.requests_per_window,
                    "window_seconds": self.window_seconds,
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_window)
        response.headers["X-RateLimit-Window"] = str(self.window_seconds)

        return response

    def _get_client_id(self, request: Request) -> Optional[str]:
        """Extract client identifier from request."""
        # Try to get user ID from headers (set by auth middleware)
        user_id = request.headers.get("X-User-Id")
        if user_id:
            return f"user:{user_id}"

        # Try to get org ID
        org_id = request.headers.get("X-Org-Id")
        if org_id:
            return f"org:{org_id}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        return f"ip:{request.client.host}" if request.client else None

    async def _check_rate_limit(self, client_id: str) -> tuple[bool, int]:
        """
        Check if client is within rate limit.
        Returns (allowed, retry_after_seconds)
        """
        now = time.time()

        if self._use_redis:
            return await self._check_rate_limit_redis(client_id, now)
        else:
            return self._check_rate_limit_memory(client_id, now)

    async def _check_rate_limit_redis(self, client_id: str, now: float) -> tuple[bool, int]:
        """Check rate limit using Redis sliding window."""
        try:
            r = await self._redis_get()
            key = f"rate_limit:{client_id}"

            # Remove old entries outside the window
            window_start = now - self.window_seconds
            await r.zremrangebyscore(key, "-inf", window_start)

            # Count requests in current window
            current_count = await r.zcard(key)

            if current_count >= self.requests_per_window:
                # Get the oldest entry to calculate retry-after
                oldest = await r.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1] + self.window_seconds - now) + 1
                    return False, max(retry_after, 1)
                return False, 1

            # Add current request
            await r.zadd(key, {str(now): now})
            # Set expiry on the sorted set
            await r.expire(key, self.window_seconds * 2)

            return True, 0

        except Exception as e:
            logger.error("rate_limit_redis_error", error=str(e))
            # Fail open - allow the request
            return True, 0

    def _check_rate_limit_memory(self, client_id: str, now: float) -> tuple[bool, int]:
        """Check rate limit using in-memory sliding window."""
        if client_id not in self._in_memory_store:
            self._in_memory_store[client_id] = []

        timestamps = self._in_memory_store[client_id]

        # Remove old entries
        window_start = now - self.window_seconds
        timestamps = [ts for ts in timestamps if ts > window_start]
        self._in_memory_store[client_id] = timestamps

        if len(timestamps) >= self.requests_per_window:
            # Calculate retry-after
            oldest = min(timestamps)
            retry_after = int(oldest + self.window_seconds - now) + 1
            return False, max(retry_after, 1)

        timestamps.append(now)
        return True, 0
