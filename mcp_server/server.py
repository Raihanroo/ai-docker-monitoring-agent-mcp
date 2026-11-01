import docker
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("docker-monitor")
client = docker.from_env()
MAX_LOG_LINES = 50


def _get(name: str):
    return client.containers.get(name)


@mcp.tool()
def list_containers() -> list[dict]:
    """List all containers with name, image and current state."""
    return [
        {
            "name": c.name,
            "image": c.image.tags[0] if c.image.tags else c.image.short_id,
            "state": c.status,
        }
        for c in client.containers.list(all=True)
    ]


@mcp.tool()
def get_container_status(name: str) -> dict:
    """Detailed status of one container: state, start time, restart count, exit code."""
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
    """Docker healthcheck result (healthy, unhealthy, starting) for one container."""
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
    """Most recent log lines of one container. Capped at 50 lines."""
    lines = min(max(lines, 1), MAX_LOG_LINES)
    return _get(name).logs(tail=lines).decode("utf-8", errors="replace")


@mcp.tool()
def check_all_services() -> dict:
    """Summary of every container's state and health in one call."""
    report = {}
    for c in client.containers.list(all=True):
        c.reload()
        health = c.attrs["State"].get("Health", {}).get("Status", "no healthcheck")
        report[c.name] = {"state": c.status, "health": health}
    return report


if __name__ == "__main__":
    mcp.run()
