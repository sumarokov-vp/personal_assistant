import json
from collections.abc import Iterator
from pathlib import Path

import anyio
import httpx
import httpx2
import pytest
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from src.todoist.models.todoist_task import TodoistTask
from tests.mcp.fake_todoist_read_client import INBOX_ID, FakeTodoistReadClient
from tests.mcp.running_core import running_core
from workers.mcp.core_server_factory import build_core_server
from workers.mcp.core_tools_factory import build_core_tools

STATIC_KEY = "test-static-key"
CORE_TOOLS = {
    "find_tasks",
    "read_task",
    "dropbox_tree",
    "dropbox_search",
    "dropbox_read",
}


@pytest.fixture
def core_url(tmp_path: Path) -> Iterator[str]:
    (tmp_path / "notes.txt").write_text("заметка", encoding="utf-8")
    todoist = FakeTodoistReadClient(
        [TodoistTask(id="t1", content="Купить молоко", project_id=INBOX_ID)]
    )
    server = build_core_server(
        build_core_tools(todoist=todoist, dropbox_root=tmp_path),
        auth=StaticTokenVerifier({STATIC_KEY: {"client_id": "test"}}),
    )
    with running_core(server) as url:
        yield url


async def list_and_find(url: str) -> tuple[set[str], dict]:
    headers = {"Authorization": f"Bearer {STATIC_KEY}"}
    async with (
        httpx2.AsyncClient(headers=headers) as http_client,
        streamable_http_client(url, http_client=http_client) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        listed = await session.list_tools()
        found = await session.call_tool("find_tasks", {})
    [content] = found.content
    assert content.type == "text"
    return {tool.name for tool in listed.tools}, json.loads(content.text)


def test_core_serves_five_tools_and_finds_fake_tasks(core_url: str):
    names, found = anyio.run(list_and_find, core_url)

    assert names == CORE_TOOLS
    assert found["count"] == 1
    assert found["tasks"][0]["title"] == "Купить молоко"


def test_core_rejects_request_without_key(core_url: str):
    response = httpx.post(
        core_url,
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        headers={"Accept": "application/json, text/event-stream"},
    )

    assert response.status_code == 401


def test_core_rejects_wrong_key(core_url: str):
    response = httpx.post(
        core_url,
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        headers={
            "Accept": "application/json, text/event-stream",
            "Authorization": "Bearer wrong",
        },
    )

    assert response.status_code == 401
