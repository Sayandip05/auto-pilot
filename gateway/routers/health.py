"""gateway/routers/health.py"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import redis.asyncio as aioredis
import httpx
import os

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "gateway"}


@router.get("/health/full")
async def health_full():
    checks = {}

    # Redis
    try:
        r = aioredis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        await r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # Agent engine
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(
                os.getenv("AGENTS_URL", "http://agents:8001") + "/health"
            )
            checks["agents"] = "ok" if resp.status_code == 200 else "degraded"
    except Exception as e:
        checks["agents"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={"status": "ok" if all_ok else "degraded", "checks": checks},
    )
