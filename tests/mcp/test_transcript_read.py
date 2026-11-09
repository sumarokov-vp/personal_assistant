import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import anyio
import httpx2
import pytest
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from tests.mcp.fake_todoist_read_client import FakeTodoistReadClient
from tests.mcp.running_core import running_core
from workers.mcp.core_server_factory import build_core_server
from workers.mcp.core_tools_factory import build_core_tools
from workers.mcp.static_key_verifier import StaticKeyVerifier

STATIC_KEY = "test-static-key"
SEGMENT_COUNT = 3000
TRANSCRIPT = "Записи разговоров/встреча.json"
NOT_RECOGNITION = "Записи разговоров/заметки.json"
NOT_JSON = "Записи разговоров/запись.txt"


def segment_text(index: int) -> str:
    return f"реплика номер {index:04d}, " + "сказано довольно длинно " * 2


@pytest.fixture
def core_url(tmp_path: Path) -> Iterator[str]:
    folder = tmp_path / "Записи разговоров"
    folder.mkdir()
    segments = [
        {"start": index * 2.5, "end": index * 2.5 + 2, "text": segment_text(index)}
        for index in range(SEGMENT_COUNT)
    ]
    (folder / "встреча.json").write_text(
        json.dumps({"text": "", "segments": segments}, ensure_ascii=False),
        encoding="utf-8",
    )
    (folder / "заметки.json").write_text('{"title": "не расшифровка"}', "utf-8")
    (folder / "запись.txt").write_text("просто текст", encoding="utf-8")
    server = build_core_server(
        build_core_tools(todoist=FakeTodoistReadClient([]), dropbox_root=tmp_path),
        auth=StaticKeyVerifier(STATIC_KEY),
    )
    with running_core(server) as url:
        yield url


async def call_core(url: str, calls: list[dict[str, Any]]) -> tuple[dict, list]:
    headers = {"Authorization": f"Bearer {STATIC_KEY}"}
    async with (
        httpx2.AsyncClient(headers=headers) as http_client,
        streamable_http_client(url, http_client=http_client) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        listed = await session.list_tools()
        results = [await session.call_tool("transcript_read", call) for call in calls]
    descriptions = {tool.name: tool.description for tool in listed.tools}
    return descriptions, results


def read_all_parts(url: str) -> list[dict]:
    _, [first] = anyio.run(call_core, url, [{"path": TRANSCRIPT}])
    head = json.loads(first.content[0].text)
    rest = [{"path": TRANSCRIPT, "part": part} for part in range(2, head["parts"] + 1)]
    _, results = anyio.run(call_core, url, rest)
    return [head, *(json.loads(result.content[0].text) for result in results)]


def test_long_transcript_comes_in_parts_that_join_without_loss(core_url: str):
    parts = read_all_parts(core_url)

    assert len(parts) > 1
    assert [part["part"] for part in parts] == list(range(1, len(parts) + 1))
    assert all(part["parts"] == len(parts) for part in parts)
    assert all(len(part["text"]) <= 40_000 for part in parts)
    lines = "".join(part["text"] for part in parts).splitlines()
    assert len(lines) == SEGMENT_COUNT
    assert [line.split("] ", 1)[1] for line in lines] == [
        segment_text(index).strip() for index in range(SEGMENT_COUNT)
    ]
    assert lines[0].startswith("[00:00:00] ")
    assert lines[-1].startswith("[02:04:57] ")


@pytest.mark.parametrize(
    "call",
    [
        {"path": NOT_RECOGNITION},
        {"path": NOT_JSON},
        {"path": TRANSCRIPT, "part": 0},
        {"path": TRANSCRIPT, "part": 999},
        {"path": "Записи разговоров/нет такого.json"},
    ],
)
def test_wrong_file_or_part_is_tool_error(core_url: str, call: dict[str, Any]):
    _, [result] = anyio.run(call_core, core_url, [call])

    assert result.is_error
    assert result.content[0].text


def test_core_lists_transcript_read_with_behaviour_for_model(core_url: str):
    descriptions, _ = anyio.run(call_core, core_url, [])

    description = descriptions["transcript_read"]
    assert "прочитать все части" in description
    assert "предложить протокол встречи или звонка" in description
    assert "Dropbox" not in description
