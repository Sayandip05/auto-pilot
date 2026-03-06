"""gateway/middleware/rate_limiter.py"""
import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = structlog.get_logger()

# Simple in-memory rate limiter (per IP). For production swap with Redis.
_request_counts: dict = {}
MAX_REQUESTS = 100   # per window
WINDOW_SECONDS = 60


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ("/health", "/health/full"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Clean up old entries
        _request_counts[client_ip] = [
            t for t in _request_counts.get(client_ip, [])
            if now - t < WINDOW_SECONDS
        ]
        _request_counts[client_ip].append(now)

        if len(_request_counts[client_ip]) > MAX_REQUESTS:
            logger.warning("rate_limiter.exceeded", ip=client_ip)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again in a minute."},
            )

        return await call_next(request)
