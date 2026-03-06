"""gateway/middleware/auth_guard.py — placeholder for route-level auth enforcement."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

PUBLIC_PATHS = {"/health", "/health/full", "/auth/token", "/webhooks/telegram",
                "/webhooks/slack/events", "/webhooks/gmail/push", "/docs", "/openapi.json"}


class AuthGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Public paths bypass JWT check (routers handle auth via Depends)
        return await call_next(request)
