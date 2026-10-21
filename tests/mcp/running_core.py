import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

import uvicorn
from fastmcp import FastMCP
from starlette.applications import Starlette

from workers.mcp.core_server_factory import MCP_PATH, build_core_app

STARTUP_TIMEOUT_SECONDS = 10


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@contextmanager
def running_app(app: Starlette, port: int) -> Iterator[str]:
    uvicorn_server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=uvicorn_server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while not uvicorn_server.started:
        assert time.monotonic() < deadline, "server did not start"
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    uvicorn_server.should_exit = True
    thread.join(timeout=STARTUP_TIMEOUT_SECONDS)


@contextmanager
def running_core(server: FastMCP, port: int | None = None) -> Iterator[str]:
    with running_app(build_core_app(server), port or free_port()) as base_url:
        yield f"{base_url}{MCP_PATH}"
