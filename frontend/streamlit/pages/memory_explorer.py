"""
frontend/streamlit/pages/memory_explorer.py
Browse, search, and manage ChromaDB vector memory.
"""

import os
import streamlit as st
import httpx

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")

st.set_page_config(page_title="Memory Explorer — Auto-Pilot", layout="wide")
st.title("🧠 Memory Explorer")
st.caption("Browse what Auto-Pilot has learned about you.")

api_key = st.session_state.get("api_key", "")
if not api_key:
    api_key = st.text_input("API Key", type="password")
if not api_key:
    st.stop()

tab1, tab2, tab3 = st.tabs(["Preferences", "Task Episodes", "Search"])

# ── Preferences Tab ───────────────────────────────────────────
with tab1:
    st.subheader("User Preferences")
    st.caption("Things Auto-Pilot has learned about your habits and preferences.")

    query = st.text_input("Search preferences", placeholder="e.g. calendar, email priority...")

    if st.button("Search Preferences") or query:
        try:
            resp = httpx.post(
                f"{GATEWAY_URL}/workflows/memory/query",
                json={"collection": "user_preferences", "query": query or "general preferences", "top_k": 10},
                headers={"X-API-Key": api_key},
                timeout=15,
            )
            if resp.status_code == 200:
                memories = resp.json().get("memories", [])
                if memories:
                    for m in memories:
                        with st.expander(m.get("content", "")[:80] + "..."):
                            st.write(m.get("content", ""))
                            st.caption(f"Metadata: {m.get('metadata', {})}")
                else:
                    st.info("No preferences stored yet.")
            else:
                st.error(f"Error: {resp.status_code}")
        except Exception as e:
            st.error(f"Error: {e}")

# ── Task Episodes Tab ─────────────────────────────────────────
with tab2:
    st.subheader("Task Episodes")
    st.caption("History of completed tasks used to inform future decisions.")

    ep_query = st.text_input("Search episodes", placeholder="e.g. price tracking, email...")

    if st.button("Search Episodes") or ep_query:
        try:
            resp = httpx.post(
                f"{GATEWAY_URL}/workflows/memory/query",
                json={"collection": "task_episodes", "query": ep_query or "recent tasks", "top_k": 10},
                headers={"X-API-Key": api_key},
                timeout=15,
            )
            if resp.status_code == 200:
                episodes = resp.json().get("memories", [])
                if episodes:
                    for ep in episodes:
                        with st.expander(ep.get("content", "")[:80] + "..."):
                            st.write(ep.get("content", ""))
                            meta = ep.get("metadata", {})
                            if meta:
                                st.caption(f"Workflow: {meta.get('workflow', '—')} | Task: {meta.get('task_id', '—')}")
                else:
                    st.info("No task episodes stored yet.")
            else:
                st.error(f"Error: {resp.status_code}")
        except Exception as e:
            st.error(f"Error: {e}")

# ── Search Tab ────────────────────────────────────────────────
with tab3:
    st.subheader("Semantic Search")
    st.caption("Search across all memory collections simultaneously.")

    collection = st.selectbox("Collection", ["user_preferences", "task_episodes", "skill_memory"])
    search_query = st.text_input("Query")
    top_k = st.slider("Results", 1, 20, 5)

    if st.button("Search") and search_query:
        try:
            resp = httpx.post(
                f"{GATEWAY_URL}/workflows/memory/query",
                json={"collection": collection, "query": search_query, "top_k": top_k},
                headers={"X-API-Key": api_key},
                timeout=15,
            )
            if resp.status_code == 200:
                results = resp.json().get("memories", [])
                st.write(f"Found {len(results)} results")
                for r in results:
                    with st.expander(r.get("content", "")[:60] + "..."):
                        st.write(r.get("content"))
                        st.json(r.get("metadata", {}))
            else:
                st.error(f"API Error: {resp.status_code}")
        except Exception as e:
            st.error(f"Error: {e}")
