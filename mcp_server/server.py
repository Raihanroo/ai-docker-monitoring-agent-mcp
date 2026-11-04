import docker
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("docker-monitor")
client = docker.from_env()
MAX_LOG_LINES = 50

# Only containers started by this project's docker-compose file are monitored.
PROJECT_LABEL = "com.docker.compose.project"
PROJECT_NAME = "docker-monitor"


def _project_containers(all_states: bool = True):
    return client.containers.list(
        all=all_states,
        filters={"label": f"{PROJECT_LABEL}={PROJECT_NAME}"},
    )


def _get(name: str):
    """Look up a container by name, only if it belongs to this project."""
    for c in _project_containers():
        if c.name == name:
            return c
    raise ValueError(f"'{name}' is not a container in project '{PROJECT_NAME}'")


@mcp.tool()
def list_containers() -> list[dict]:
    """List all project containers with name, image and current state."""
    return [
        {
            "name": c.name,
            "image": c.image.tags[0] if c.image.tags else c.image.short_id,
            "state": c.status,
        }
        for c in _project_containers()
    ]


@mcp.tool()
def get_container_status(name: str) -> dict:
    """Detailed status of one project container: state, start time, restart count, exit code."""
    c = _get(name)
    c.reload()
    state = c.attrs["State"]
    return {
        "name": c.name,
        "status": c.status,
        "started_at": state.get("StartedAt"),
        "restart_count": c.attrs.get("RestartCount", 0),
        "exit_code": state.get("ExitCode"),
    }


@mcp.tool()
def get_container_health(name: str) -> dict:
    """Docker healthcheck result (healthy, unhealthy, starting) for one project container."""
    c = _get(name)
    c.reload()
    health = c.attrs["State"].get("Health")
    if not health:
        return {"name": c.name, "health": "no healthcheck defined"}
    last = health["Log"][-1] if health.get("Log") else None
    return {
        "name": c.name,
        "health": health["Status"],
        "last_output": last["Output"].strip() if last else None,
    }


@mcp.tool()
def get_container_logs(name: str, lines: int = 50) -> str:
    """Most recent log lines of one project container. Capped at 50 lines."""
    lines = min(max(lines, 1), MAX_LOG_LINES)
    return _get(name).logs(tail=lines).decode("utf-8", errors="replace")


@mcp.tool()
def check_all_services() -> dict:
    """Summary of every project container's state and health in one call."""
    report = {}
    for c in _project_containers():
        c.reload()
        health = c.attrs["State"].get("Health", {}).get("Status", "no healthcheck")
        report[c.name] = {"state": c.status, "health": health}
    return report


if __name__ == "__main__":
    mcp.run()
