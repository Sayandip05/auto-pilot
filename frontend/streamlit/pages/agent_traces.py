"""
frontend/streamlit/pages/agent_traces.py
LangSmith trace viewer — shows agent execution traces.
"""

import os
import streamlit as st
import httpx

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
LANGSMITH_PROJECT = os.getenv("LANGCHAIN_PROJECT", "auto-pilot")
LANGSMITH_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")

st.set_page_config(page_title="Agent Traces — Auto-Pilot", layout="wide")
st.title("🔍 Agent Traces")
st.caption("Inspect every reasoning step and agent handoff.")

api_key = st.session_state.get("api_key", "")
if not api_key:
    api_key = st.text_input("API Key", type="password")
if not api_key:
    st.stop()

# ── LangSmith Link ────────────────────────────────────────────
if LANGSMITH_API_KEY:
    st.info(
        f"🔗 Full traces are available in [LangSmith](https://smith.langchain.com/o/auto-pilot/projects/{LANGSMITH_PROJECT}). "
        "The view below shows recent task trace summaries from your gateway."
    )
else:
    st.warning("LANGCHAIN_API_KEY not set. Set it in .env to enable full LangSmith tracing.")

st.divider()

# ── Recent Traces from Gateway ────────────────────────────────
st.subheader("Recent Task Traces")

try:
    resp = httpx.get(
        f"{GATEWAY_URL}/workflows/?limit=20",
        headers={"X-API-Key": api_key},
        timeout=10,
    )
    tasks = resp.json().get("tasks", []) if resp.status_code == 200 else []
except Exception as e:
    tasks = []
    st.error(f"Error: {e}")

if not tasks:
    st.info("No tasks found. Run a workflow first.")
    st.stop()

for task in tasks:
    task_id = task.get("id", "")
    status = task.get("status", "")
    workflow = task.get("workflow_type", "")
    trace_id = task.get("agent_trace_id", "")
    duration = task.get("duration_ms", 0)
    tokens = task.get("tokens_used", 0)

    emoji = {"completed": "✅", "running": "⏳", "failed": "❌", "pending": "🕐"}.get(status, "❓")

    with st.expander(f"{emoji} [{workflow}] — {task_id[:8]}... | {status} | {duration}ms | {tokens} tokens"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Task ID:** `{task_id}`")
            st.write(f"**Workflow:** {workflow}")
            st.write(f"**Status:** {status}")
        with col2:
            st.write(f"**Duration:** {duration}ms")
            st.write(f"**Tokens Used:** {tokens}")
            if trace_id:
                st.write(f"**LangSmith Trace:** [{trace_id[:12]}...](https://smith.langchain.com)")

        # Fetch full task detail
        if st.button(f"Load Full Detail", key=f"detail_{task_id}"):
            try:
                detail_resp = httpx.get(
                    f"{GATEWAY_URL}/workflows/{task_id}",
                    headers={"X-API-Key": api_key},
                    timeout=10,
                )
                if detail_resp.status_code == 200:
                    st.json(detail_resp.json())
            except Exception as ex:
                st.error(f"Error: {ex}")

st.divider()
st.subheader("📊 Eval Results")
st.info("Run `python evals/run_evals.py` locally to see eval scores here, or check your LangSmith project dashboard.")
