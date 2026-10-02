from pathlib import Path

import anyio
from fastmcp import Client

from tests.mcp.fake_todoist_read_client import FakeTodoistReadClient
from workers.mcp.core_server_factory import build_core_server
from workers.mcp.core_tools_factory import build_core_tools
from workers.mcp.static_key_verifier import StaticKeyVerifier


async def call_with_wrong_arguments(dropbox_root: Path) -> tuple[bool, str]:
    server = build_core_server(
        build_core_tools(FakeTodoistReadClient([]), dropbox_root),
        auth=StaticKeyVerifier("key"),
    )
    async with Client(server) as client:
        result = await client.call_tool("read_task", {"ref": "x"}, raise_on_error=False)
    [content] = result.content
    assert content.type == "text"
    return result.is_error, content.text


def test_wrong_arguments_reach_model_as_tool_error_not_protocol_error(tmp_path: Path):
    is_error, text = anyio.run(call_with_wrong_arguments, tmp_path)

    assert is_error
    assert "task_ref" in text
