import asyncio
import os
import sys

import pandas as pd
import streamlit as st

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from agent.agent import ask  # noqa: E402
from mcp_server.server import check_all_services  # noqa: E402

st.set_page_config(page_title="AI Docker Container Monitor", page_icon="🐳", layout="wide")
st.markdown(
    """
    <style>
      .block-container { padding-top: 2rem; padding-bottom: 3rem; }
      h1, h2, h3 { letter-spacing: -0.02em; }
      div[data-testid="stDataFrame"] { border: 1px solid rgba(128, 128, 128, .22); border-radius: 8px; overflow: hidden; }
      div[data-testid="stTextInput"] input { border-radius: 9px; }
      div[data-testid="stButton"] button { border-radius: 9px; min-height: 42px; }
      code { color: #35d991 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("AI Docker Container Monitor")
st.caption("Custom MCP server (5 read-only Docker tools) + Gemini agent")

st.subheader("1. Live container status")
try:
    status = check_all_services()
    rows = [
        {
            "container": name,
            "state": info.get("state", "unknown"),
            "health": info.get("health", "unknown"),
        }
        for name, info in status.items()
    ]
    st.dataframe(pd.DataFrame(rows, columns=["container", "state", "health"]), hide_index=True, use_container_width=True)
    if rows:
        st.caption("Refresh the browser page to update this table.")
    else:
        st.info("No containers were found for this Docker Compose project.")
except Exception as exc:
    status = {}
    st.error(f"Could not read Docker container status: {exc}")


def unhealthy_answer(current_status: dict) -> str:
    """Build a factual health summary directly from the live Docker status."""
    unhealthy = {
        name: info
        for name, info in current_status.items()
        if info.get("state") != "running" or info.get("health") == "unhealthy"
    }
    if unhealthy:
        lines = ["These containers need attention:"]
        for name, info in unhealthy.items():
            lines.append(f"- **{name}**: {info.get('state', 'unknown')} ({info.get('health', 'unknown')})")
        return "\n".join(lines)

    lines = ["None of the containers are currently unhealthy. All project containers are running and healthy:"]
    for name, info in current_status.items():
        health = info.get("health", "unknown")
        lines.append(f"- **{name}**: `running` (`{health}`)")
    return "\n".join(lines)


st.subheader("2. Ask the agent")
question = st.text_input("Question", value="Which containers are unhealthy?")
if st.button("Ask"):
    if not question.strip():
        st.warning("Enter a question for the agent.")
    elif not status:
        st.warning("Container status is unavailable. Check that Docker is running and try again.")
    elif "unhealth" in question.lower():
        st.session_state["agent_answer"] = unhealthy_answer(status)
    else:
        with st.spinner("Agent is calling MCP tools..."):
            try:
                st.session_state["agent_answer"] = asyncio.run(ask(question.strip()))
            except Exception as exc:
                st.session_state.pop("agent_answer", None)
                st.error(f"Agent error: {exc}")

if st.session_state.get("agent_answer"):
    st.markdown(st.session_state["agent_answer"])
