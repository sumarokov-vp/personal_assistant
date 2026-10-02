import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import anyio
import httpx2
import pytest
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp_types import CallToolResult, Implementation, RequestParamsMeta

from tests.mcp.fake_todoist_read_client import FakeTodoistReadClient
from tests.mcp.running_core import running_core
from workers.mcp.core_server_factory import build_core_middleware, build_core_server
from workers.mcp.core_tools_factory import build_core_tools
from workers.mcp.journal.json_lines_file import JsonLinesFile
from workers.mcp.static_key_verifier import StaticKeyVerifier

STATIC_KEY = "journal-secret-key"
CLIENT_NAME = "journal-test-client"
ALLOWED_PROJECT = "a"
TRACE_META = cast(RequestParamsMeta, {"trace": "t-1"})


@pytest.fixture
def journal_file(tmp_path: Path) -> Path:
    return tmp_path / "mcp" / "requests.jsonl"


@pytest.fixture
def core_url(tmp_path: Path, journal_file: Path) -> Iterator[str]:
    journal_file.parent.mkdir()
    server = build_core_server(
        build_core_tools(todoist=FakeTodoistReadClient([]), dropbox_root=tmp_path),
        auth=StaticKeyVerifier(STATIC_KEY),
        middleware=build_core_middleware(
            JsonLinesFile(journal_file), {ALLOWED_PROJECT}
        ),
    )
    with running_core(server) as url:
        yield url


async def call_tool(
    url: str, headers: dict[str, str], name: str, arguments: dict[str, Any]
) -> CallToolResult:
    async with (
        httpx2.AsyncClient(
            headers={"Authorization": f"Bearer {STATIC_KEY}", **headers}
        ) as http,
        streamable_http_client(url, http_client=http) as (read, write),
        ClientSession(
            read, write, client_info=Implementation(name=CLIENT_NAME, version="1")
        ) as session,
    ):
        await session.initialize()
        return await session.call_tool(name, arguments, meta=TRACE_META)


def journal_lines(journal_file: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in journal_file.read_text(encoding="utf-8").splitlines()
    ]


def tool_calls(journal_file: Path) -> list[dict[str, Any]]:
    return [
        line for line in journal_lines(journal_file) if line["method"] == "tools/call"
    ]


def test_project_header_is_journaled_as_header_source(
    core_url: str, journal_file: Path
):
    result = anyio.run(
        call_tool, core_url, {"X-Project": ALLOWED_PROJECT}, "find_tasks", {}
    )

    assert not result.is_error
    [call] = tool_calls(journal_file)
    assert call["tool"] == "find_tasks"
    assert call["project"] == ALLOWED_PROJECT
    assert call["project_source"] == "header"
    assert call["outcome"] == "ok"
    assert call["meta"]["trace"] == "t-1"


def test_foreign_project_parameter_is_denied_without_calling_tool(
    core_url: str, journal_file: Path
):
    result = anyio.run(call_tool, core_url, {}, "read_task", {"project": "чужой"})

    assert result.is_error
    [content] = result.content
    assert content.type == "text"
    assert "не разрешён" in content.text
    [call] = tool_calls(journal_file)
    assert call["project"] == "чужой"
    assert call["project_source"] == "param"
    assert call["outcome"] == "denied"


def test_allowed_project_parameter_is_stripped_before_tool_input(
    core_url: str, journal_file: Path
):
    result = anyio.run(
        call_tool, core_url, {}, "find_tasks", {"project": ALLOWED_PROJECT}
    )

    assert not result.is_error
    [call] = tool_calls(journal_file)
    assert (call["project"], call["project_source"], call["outcome"]) == (
        ALLOWED_PROJECT,
        "param",
        "ok",
    )


def test_tool_failure_without_project_is_journaled_as_error(
    core_url: str, journal_file: Path
):
    result = anyio.run(call_tool, core_url, {}, "read_task", {"ref": "x"})

    assert result.is_error
    [call] = tool_calls(journal_file)
    assert (call["project"], call["project_source"], call["outcome"]) == (
        None,
        "none",
        "error",
    )


def test_initialize_is_journaled_with_client_name_and_masked_key(
    core_url: str, journal_file: Path
):
    anyio.run(call_tool, core_url, {"X-Api-Key": "other-secret"}, "find_tasks", {})

    [initialize] = [
        line for line in journal_lines(journal_file) if line["method"] == "initialize"
    ]
    assert initialize["client"]["name"] == CLIENT_NAME
    assert initialize["headers"]["authorization"] == "***"
    journal_text = journal_file.read_text(encoding="utf-8")
    assert STATIC_KEY not in journal_text
    assert "other-secret" not in journal_text
