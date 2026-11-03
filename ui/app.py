import asyncio
import os
import sys

import pandas as pd
import streamlit as st

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from agent.agent import ask  # noqa: E402
from mcp_server.server import check_all_services  # noqa: E402

st.set_page_config(page_title="Docker Monitor", layout="wide")
st.title("AI Docker Container Monitor")
st.caption("Custom MCP server (5 read-only Docker tools) + Gemini agent")

st.subheader("1. Live container status")
status = check_all_services()
df = pd.DataFrame([{"container": name, **info} for name, info in status.items()])
st.dataframe(df, hide_index=True)
st.caption("Refresh the browser page to update this table.")

st.subheader("2. Ask the agent")
question = st.text_input("Question", value="Are all services running properly?")
if st.button("Ask"):
    with st.spinner("Agent is calling MCP tools..."):
        try:
            answer = asyncio.run(ask(question))
            st.markdown(answer)
        except Exception as e:
            st.error(f"Agent error: {e}")
