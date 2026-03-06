"""
gateway/routers/price_tracker.py
Dedicated REST endpoints for the Price Tracker feature.
Mounted at /price-tracker in gateway/main.py.
"""

from __future__ import annotations
import uuid
import structlog
import httpx
import os

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, AnyHttpUrl, field_validator
from typing import Optional

from routers.auth import verify_token

logger = structlog.get_logger()
router = APIRouter()

AGENTS_URL = os.getenv("AGENTS_URL", "http://agents:8001")


# ── Pydantic models ───────────────────────────────────────────

class TrackCreateRequest(BaseModel):
    url: str
    alert_threshold: Optional[float] = None

    @field_validator("alert_threshold")
    @classmethod
    def threshold_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("alert_threshold must be greater than 0")
        return v


class TrackResponse(BaseModel):
    task_id: str
    status: str
    message: str


# ── Helpers ───────────────────────────────────────────────────

async def _dispatch(task_id: str, workflow_type: str, input_data: dict, user_key: str):
    """Fire-and-forget task dispatch to agent engine."""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            await client.post(
                f"{AGENTS_URL}/tasks",
                json={
                    "task_id": task_id,
                    "workflow_type": workflow_type,
                    "input_data": input_data,
                    "user_key": user_key,
                },
            )
    except Exception as e:
        logger.error("price_tracker.dispatch_failed", task_id=task_id, error=str(e))


# ── Endpoints ─────────────────────────────────────────────────

@router.post("/", response_model=TrackResponse, summary="Start tracking a product price")
async def create_price_track(
    body: TrackCreateRequest,
    background_tasks: BackgroundTasks,
    payload: dict = Depends(verify_token),
):
    """
    Set up a new price tracker for a product URL.
    The agent scrapes the current price as a baseline and schedules 6-hourly checks.
    """
    task_id = str(uuid.uuid4())
    user_key = payload.get("sub", "unknown")

    logger.info(
        "price_tracker.create",
        task_id=task_id,
        url=body.url,
        threshold=body.alert_threshold,
        user=user_key,
    )

    background_tasks.add_task(
        _dispatch,
        task_id,
        "price_tracker",
        {"url": body.url, "alert_threshold": body.alert_threshold},
        user_key,
    )

    return TrackResponse(
        task_id=task_id,
        status="accepted",
        message=f"Price tracking started ✅ (Task #{task_id[:8]}). "
                f"{'Alert set for below ' + str(body.alert_threshold) + '.' if body.alert_threshold else 'No alert threshold set.'}",
    )


@router.get("/", summary="List all active price tracks for current user")
async def list_price_tracks(payload: dict = Depends(verify_token)):
    """Return all active price tracks for the authenticated user."""
    user_key = payload.get("sub", "unknown")
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "database"))
        from models.price_tracks import list_active_tracks
        tracks = await list_active_tracks(user_id=user_key)
        return {"tracks": tracks, "count": len(tracks)}
    except Exception as e:
        logger.error("price_tracker.list_error", error=str(e))
        raise HTTPException(status_code=503, detail="Database unavailable")


@router.get("/{track_id}", summary="Get a single price track with history")
async def get_price_track(track_id: str, payload: dict = Depends(verify_token)):
    """Fetch track metadata and recent price history."""
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "database"))
        from models.price_tracks import get_track, get_price_history, get_price_stats

        track = await get_track(track_id)
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")

        history = await get_price_history(track_id, limit=50)
        stats = await get_price_stats(track_id)

        return {"track": track, "history": history, "stats": stats}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("price_tracker.get_error", error=str(e))
        raise HTTPException(status_code=503, detail="Database unavailable")


@router.delete("/{track_id}", summary="Stop tracking a product")
async def delete_price_track(track_id: str, payload: dict = Depends(verify_token)):
    """Deactivate a price track (soft delete)."""
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "database"))
        from models.price_tracks import deactivate_track

        success = await deactivate_track(track_id)
        if not success:
            raise HTTPException(status_code=404, detail="Track not found or already inactive")
        return {"track_id": track_id, "status": "deactivated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("price_tracker.delete_error", error=str(e))
        raise HTTPException(status_code=503, detail="Database unavailable")


@router.post("/{track_id}/check", summary="Manually trigger a price check")
async def manual_price_check(
    track_id: str,
    background_tasks: BackgroundTasks,
    payload: dict = Depends(verify_token),
):
    """Force an immediate re-scrape for a tracked product."""
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "database"))
        from models.price_tracks import get_track

        track = await get_track(track_id)
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")

    task_id = str(uuid.uuid4())
    user_key = payload.get("sub", "unknown")

    background_tasks.add_task(
        _dispatch,
        task_id,
        "price_tracker_check",
        {
            "track_id": track_id,
            "url": track["product_url"],
            "alert_threshold": float(track["alert_threshold"]) if track.get("alert_threshold") else None,
            "current_price": float(track["current_price"]) if track.get("current_price") else None,
        },
        user_key,
    )

    return {"task_id": task_id, "status": "accepted", "message": "Manual price check queued ✅"}
