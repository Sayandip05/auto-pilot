"""
frontend/streamlit/app.py
Auto-Pilot Streamlit Dashboard — main entry point.
"""

import os
import streamlit as st

st.set_page_config(
    page_title="Auto-Pilot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.title("🤖 Auto-Pilot")
    st.caption("Production-Grade Personal Agent System")
    st.divider()

    api_key = st.text_input("API Key", type="password", key="api_key")
    if api_key:
        st.success("✅ API key set")
    else:
        st.warning("Enter your API key to continue")

    st.divider()
    st.markdown("**Navigation**")
    st.page_link("pages/dashboard.py",        label="📊 Dashboard",       icon="📊")
    st.page_link("pages/task_history.py",      label="📋 Task History",    icon="📋")
    st.page_link("pages/memory_explorer.py",   label="🧠 Memory Explorer", icon="🧠")
    st.page_link("pages/agent_traces.py",      label="🔍 Agent Traces",    icon="🔍")

# ── Home ──────────────────────────────────────────────────────
st.title("🤖 Auto-Pilot Dashboard")
st.markdown(
    "Welcome to Auto-Pilot — your production-grade personal agent system.\n\n"
    "Use the sidebar to navigate between views, or trigger a workflow below."
)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Status", "🟢 Online" if api_key else "⚫ No Key")

with col2:
    if api_key:
        import httpx
        try:
            resp = httpx.get(f"{GATEWAY_URL}/health", timeout=3)
            st.metric("Gateway", "🟢 Healthy")
        except Exception:
            st.metric("Gateway", "🔴 Offline")
    else:
        st.metric("Gateway", "—")

with col3:
    st.metric("Version", "1.0.0")

st.divider()

# Quick trigger
st.subheader("⚡ Quick Trigger")

workflow = st.selectbox(
    "Workflow",
    ["price_tracker", "email_to_calendar", "file_organizer", "slack_to_notion", "social_poster"],
)

with st.expander("Input Data (JSON)", expanded=True):
    import json

    defaults = {
        "price_tracker": '{"url": "https://amazon.com/...", "alert_threshold": 50}',
        "email_to_calendar": '{}',
        "file_organizer": '{"dry_run": true}',
        "slack_to_notion": '{}',
        "social_poster": '{"text": "Hello world!", "platform": "twitter"}',
    }
    input_json = st.text_area("JSON", value=defaults.get(workflow, "{}"), height=80)

if st.button("🚀 Trigger Workflow", disabled=not api_key):
    try:
        import httpx as _httpx
        input_data = json.loads(input_json)
        with st.spinner("Running..."):
            resp = _httpx.post(
                f"{GATEWAY_URL}/workflows/trigger",
                json={"workflow_type": workflow, "input_data": input_data},
                headers={"X-API-Key": api_key},
                timeout=120,
            )
        data = resp.json()
        st.success(f"✅ Task `{data.get('task_id')}` created")
        st.json(data)
    except json.JSONDecodeError:
        st.error("Invalid JSON in input data")
    except Exception as e:
        st.error(f"Error: {e}")
