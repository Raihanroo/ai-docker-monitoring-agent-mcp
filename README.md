# AI-Powered Docker Container Monitoring Agent (MCP)

A Gemini-powered agent that answers natural-language questions about the health of local Docker containers. It talks to a custom read-only MCP server, which wraps the Docker Engine API.


## Components

| Path | Purpose |
|---|---|
| `docker-compose.yml` | Runs `sales-chatbot`, `app-db` (Postgres) and `app-web` (nginx), each with a healthcheck |
| `chatbot/` | Placeholder chatbot service with a `/health` endpoint |
| `mcp_server/server.py` | FastMCP server exposing five read-only Docker tools |
| `agent/agent.py` | Gemini client that calls MCP tools and summarizes the results |

## MCP tools

| Tool | Description |
|---|---|
| `list_containers` | All containers with name, image and state |
| `get_container_status` | State, start time, restart count, exit code for one container |
| `get_container_health` | Docker healthcheck status and last output for one container |
| `get_container_logs` | Most recent log lines (capped at 50) |
| `check_all_services` | State and health of every container in one call |

The tools are read-only. The server cannot start, stop or delete containers.

## Requirements

- Linux or WSL2 with Docker Engine and Docker Compose
- Python 3.12 or newer
- A Gemini API key from Google AI Studio

## Setup

```bash
git clone https://github.com/Raihanroo/ai-docker-monitoring-agent-mcp.git
cd ai-docker-monitoring-agent-mcp
cp .env.example .env              # then put your real key in .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r mcp_server/requirements.txt
```

## Run

```bash
docker compose up -d --build
docker compose ps                 # wait until services show (healthy)
python agent/agent.py "Are all services running properly?"
```

## Web UI

A browser dashboard that shows live container status and lets you ask the agent questions.

```bash
streamlit run ui/app.py
```

Then open http://localhost:8501 in your browser.

- **Live container status:** table of all containers, refreshed when the page reloads.
- **Ask the agent:** type a question and press Ask. The agent calls the MCP tools and shows the answer.

The UI uses the same MCP server and agent code as the command-line agent, so there is no duplication.

## Test results

| # | Test case | Action | Expected | Actual | Result |
|---|---|---|---|---|---|
| 1 | All healthy | Compose up, ask status | All project services healthy | app-db, app-web, sales-chatbot healthy | PASS |
| 2 | Service stopped | Stop sales-chatbot, ask status | Chatbot reported as down | Agent reported sales-chatbot as exited (exit 137) and app-web/app-db as healthy. Note: the health label said "unhealthy" for a stopped container | PASS (with note) |
| 3 | Unhealthy service | Pause app-db so healthcheck fails | DB reported unhealthy | docker inspect showed unhealthy; agent reported app-db as paused and unhealthy. Note: used docker pause instead of editing the healthcheck | PASS (with note) |
| 4 | Log inspection | Ask why chatbot is failing | Agent fetches logs and summarizes | Agent read sales-chatbot logs (200 OK, no errors) and said the chatbot is healthy. It also assumed n8n was a dependency of the chatbot, which is not true in this project | PASS (with note) |
| 5 | Recovery | Stop and restart sales-chatbot, ask again | System reported normal | Docker: sales-chatbot back to running and healthy after restart. Agent confirmed all three project containers healthy (app-db, app-web, sales-chatbot). n8n and serene_tharp reported as non-project containers | PASS |

## Limitations

- Monitoring is on demand. The agent checks live state when asked; there is no background polling.
- No alerting (email or chat) and no automatic restart in version 1.
- Only the local Docker host is supported.
- Containers outside this project (for example `n8n`) also appear in `check_all_services`, since the tools inspect every container on the host.
- Model names change over time. `gemini-3.5-flash` was used during testing; update `MODEL` in `agent/agent.py` if Google retires it.
