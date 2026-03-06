"""
frontend/streamlit/pages/dashboard.py
Live workflow status and system overview.
"""

import os
import streamlit as st
import httpx
import pandas as pd
from datetime import datetime

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")

st.set_page_config(page_title="Dashboard — Auto-Pilot", layout="wide")
st.title("📊 Live Dashboard")

api_key = st.session_state.get("api_key", "")
if not api_key:
    api_key = st.text_input("API Key", type="password")

if not api_key:
    st.warning("Enter your API key in the sidebar or above.")
    st.stop()

# ── Refresh ───────────────────────────────────────────────────
auto_refresh = st.toggle("Auto-refresh (30s)", value=False)
if auto_refresh:
    import time
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# ── Metrics ───────────────────────────────────────────────────
try:
    resp = httpx.get(
        f"{GATEWAY_URL}/workflows/stats",
        headers={"X-API-Key": api_key},
        timeout=10,
    )
    stats = resp.json() if resp.status_code == 200 else {}
except Exception:
    stats = {}

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Tasks", stats.get("total", "—"))
col2.metric("Completed", stats.get("completed", "—"))
col3.metric("Running", stats.get("running", "—"))
col4.metric("Failed", stats.get("failed", "—"))

st.divider()

# ── Active Tasks ──────────────────────────────────────────────
st.subheader("⏳ Active Tasks")

try:
    resp = httpx.get(
        f"{GATEWAY_URL}/workflows/?status=running&limit=20",
        headers={"X-API-Key": api_key},
        timeout=10,
    )
    active = resp.json().get("tasks", []) if resp.status_code == 200 else []
except Exception as e:
    active = []
    st.error(f"Could not fetch active tasks: {e}")

if active:
    df = pd.DataFrame(active)
    st.dataframe(df, use_container_width=True)
else:
    st.info("No active tasks right now.")

st.divider()

# ── Recent Completions ────────────────────────────────────────
st.subheader("✅ Recent Completions")

try:
    resp = httpx.get(
        f"{GATEWAY_URL}/workflows/?status=completed&limit=10",
        headers={"X-API-Key": api_key},
        timeout=10,
    )
    recent = resp.json().get("tasks", []) if resp.status_code == 200 else []
except Exception:
    recent = []

if recent:
    df = pd.DataFrame(recent)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"])
    st.dataframe(df[["id", "workflow_type", "status", "created_at"]].head(10), use_container_width=True)
else:
    st.info("No completed tasks yet.")

if auto_refresh:
    import time
    time.sleep(30)
    st.rerun()
