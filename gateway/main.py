"""
gateway/main.py
FastAPI application — single entry point for all client interfaces.
"""

import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import workflows, webhooks, auth, health, price_tracker
from middleware.rate_limiter import RateLimiterMiddleware
from middleware.auth_guard import AuthGuardMiddleware

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("gateway.startup", service="gateway")
    yield
    logger.info("gateway.shutdown", service="gateway")


app = FastAPI(
    title="Auto-Pilot API Gateway",
    description="Production-grade personal agent system — API Gateway",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimiterMiddleware)

# ── Routers ───────────────────────────────────────────────────
app.include_router(health.router,     prefix="",           tags=["Health"])
app.include_router(auth.router,       prefix="/auth",      tags=["Auth"])
app.include_router(workflows.router,  prefix="/workflows", tags=["Workflows"])
app.include_router(webhooks.router,       prefix="/webhooks",      tags=["Webhooks"])
app.include_router(price_tracker.router,  prefix="/price-tracker", tags=["Price Tracker"])


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("gateway.unhandled_error", error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
