"""
frontend/streamlit/pages/task_history.py
Full task history with filtering and detail view.
"""

import os
import streamlit as st
import httpx
import pandas as pd

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")

st.set_page_config(page_title="Task History — Auto-Pilot", layout="wide")
st.title("📋 Task History")

api_key = st.session_state.get("api_key", "")
if not api_key:
    api_key = st.text_input("API Key", type="password")
if not api_key:
    st.stop()

# ── Filters ───────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    status_filter = st.selectbox("Status", ["all", "completed", "running", "failed", "pending"])
with col2:
    workflow_filter = st.selectbox(
        "Workflow",
        ["all", "price_tracker", "email_to_calendar", "file_organizer", "slack_to_notion", "social_poster"],
    )
with col3:
    limit = st.number_input("Limit", min_value=10, max_value=200, value=50, step=10)

# ── Fetch ─────────────────────────────────────────────────────
params = {"limit": limit}
if status_filter != "all":
    params["status"] = status_filter
if workflow_filter != "all":
    params["workflow_type"] = workflow_filter

try:
    resp = httpx.get(
        f"{GATEWAY_URL}/workflows/",
        params=params,
        headers={"X-API-Key": api_key},
        timeout=15,
    )
    tasks = resp.json().get("tasks", []) if resp.status_code == 200 else []
except Exception as e:
    tasks = []
    st.error(f"Error fetching tasks: {e}")

st.caption(f"Showing {len(tasks)} tasks")

if not tasks:
    st.info("No tasks match the current filter.")
    st.stop()

df = pd.DataFrame(tasks)

# ── Table ─────────────────────────────────────────────────────
display_cols = [c for c in ["id", "workflow_type", "status", "created_at", "duration_ms", "tokens_used"] if c in df.columns]
st.dataframe(df[display_cols], use_container_width=True, height=400)

st.divider()

# ── Detail View ───────────────────────────────────────────────
st.subheader("🔎 Task Detail")
task_id = st.text_input("Enter Task ID to inspect")

if task_id:
    try:
        resp = httpx.get(
            f"{GATEWAY_URL}/workflows/{task_id}",
            headers={"X-API-Key": api_key},
            timeout=10,
        )
        if resp.status_code == 200:
            task = resp.json()
            st.json(task)
        else:
            st.error(f"Task not found: {resp.status_code}")
    except Exception as e:
        st.error(f"Error: {e}")
