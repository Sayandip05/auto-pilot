"""
database/models/price_tracks.py
Async CRUD helpers for price_tracks and price_history tables.
Uses asyncpg directly — no ORM overhead.
"""

from __future__ import annotations
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import asyncpg
import structlog

logger = structlog.get_logger()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://autopilot:autopilot@localhost:5432/autopilot"
)


async def _conn() -> asyncpg.Connection:
    return await asyncpg.connect(DATABASE_URL)


# ── price_tracks ──────────────────────────────────────────────

async def create_track(
    user_id: str,
    product_url: str,
    product_name: str,
    baseline_price: float,
    alert_threshold: Optional[float] = None,
    schedule_id: Optional[str] = None,
) -> dict:
    """Insert a new price track row and return it."""
    conn = await _conn()
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO price_tracks
              (id, user_id, product_url, product_name, baseline_price,
               current_price, alert_threshold, is_active, schedule_id)
            VALUES ($1, $2, $3, $4, $5, $5, $6, true, $7)
            RETURNING *
            """,
            str(uuid.uuid4()),
            user_id,
            product_url,
            product_name,
            baseline_price,
            alert_threshold,
            schedule_id,
        )
        logger.info("price_tracks.created", user=user_id, product=product_name)
        return dict(row)
    finally:
        await conn.close()


async def get_track(track_id: str) -> Optional[dict]:
    conn = await _conn()
    try:
        row = await conn.fetchrow(
            "SELECT * FROM price_tracks WHERE id = $1", track_id
        )
        return dict(row) if row else None
    finally:
        await conn.close()


async def list_active_tracks(user_id: Optional[str] = None) -> list[dict]:
    """Fetch all active tracks, optionally filtered by user."""
    conn = await _conn()
    try:
        if user_id:
            rows = await conn.fetch(
                "SELECT * FROM price_tracks WHERE is_active = true AND user_id = $1"
                " ORDER BY created_at DESC",
                user_id,
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM price_tracks WHERE is_active = true"
                " ORDER BY last_checked_at NULLS FIRST LIMIT 50"
            )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def update_current_price(track_id: str, new_price: float) -> None:
    """Update current_price and last_checked_at after a successful scrape."""
    conn = await _conn()
    try:
        await conn.execute(
            """
            UPDATE price_tracks
            SET current_price = $1, last_checked_at = NOW()
            WHERE id = $2
            """,
            new_price,
            track_id,
        )
        logger.info("price_tracks.price_updated", track_id=track_id, new_price=new_price)
    finally:
        await conn.close()


async def deactivate_track(track_id: str) -> bool:
    """Soft-delete: mark is_active = false."""
    conn = await _conn()
    try:
        result = await conn.execute(
            "UPDATE price_tracks SET is_active = false WHERE id = $1", track_id
        )
        return result == "UPDATE 1"
    finally:
        await conn.close()


# ── price_history ─────────────────────────────────────────────

async def append_price_history(track_id: str, price: float) -> None:
    """Append a price data point to the history table."""
    conn = await _conn()
    try:
        await conn.execute(
            "INSERT INTO price_history (id, track_id, price) VALUES ($1, $2, $3)",
            str(uuid.uuid4()),
            track_id,
            price,
        )
    finally:
        await conn.close()


async def get_price_history(track_id: str, limit: int = 50) -> list[dict]:
    """Fetch the most recent price history for a track."""
    conn = await _conn()
    try:
        rows = await conn.fetch(
            """
            SELECT price, recorded_at
            FROM price_history
            WHERE track_id = $1
            ORDER BY recorded_at DESC
            LIMIT $2
            """,
            track_id,
            limit,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_price_stats(track_id: str) -> dict:
    """Return min / max / avg price and total data points."""
    conn = await _conn()
    try:
        row = await conn.fetchrow(
            """
            SELECT
              COUNT(*)            AS data_points,
              MIN(price)          AS min_price,
              MAX(price)          AS max_price,
              ROUND(AVG(price)::numeric, 2) AS avg_price,
              MIN(recorded_at)    AS first_seen,
              MAX(recorded_at)    AS last_seen
            FROM price_history
            WHERE track_id = $1
            """,
            track_id,
        )
        return dict(row) if row else {}
    finally:
        await conn.close()
