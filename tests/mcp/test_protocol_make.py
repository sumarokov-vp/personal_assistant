import json
import shutil
from collections.abc import Iterator
from io import BytesIO
from pathlib import Path
from typing import Any

import anyio
import httpx2
import pytest
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pypdf import PdfReader

from tests.mcp.fake_todoist_read_client import FakeTodoistReadClient
from tests.mcp.running_core import running_core
from workers.mcp.core_server_factory import build_core_server
from workers.mcp.core_tools_factory import build_core_tools
from workers.mcp.static_key_verifier import StaticKeyVerifier

pytestmark = pytest.mark.skipif(
    shutil.which("typst") is None,
    reason="typst нет в PATH — протокол не собрать (в образе ядра typst есть)",
)

STATIC_KEY = "test-static-key"
RECORDINGS = "Записи разговоров"
LITERAL_LINE = "Тариф #2 и *звёздочка* _подчерк_ @метка $5 <тег> `код` \\слэш [скобка]"
ACTION = "Прислать смету по второму этапу"

COMMON: dict[str, Any] = {
    "title": "Клиент: этап два",
    "date": "05.11.2026",
    "parties": {"Smartist": ["Владимир"], "Клиент": ["руководитель"]},
    "agreements": ["Второй этап начинаем в декабре", LITERAL_LINE],
    "actions": [{"what": ACTION, "who": "Smartist", "due": "12.11.2026"}],
    "open_questions": ["Кто подписывает акт — к клиенту"],
}
MEETING = {
    **COMMON,
    "kind": "meeting",
    "agenda": ["Сроки второго этапа"],
    "discussion": [{"topic": "Сроки", "points": ["Старт после приёмки первого"]}],
}
CALL = {**COMMON, "kind": "call", "title": "Клиент: созвон о сроках"}


@pytest.fixture
def storage_root(tmp_path: Path) -> Path:
    (tmp_path / RECORDINGS).mkdir()
    return tmp_path


@pytest.fixture
def core_url(storage_root: Path) -> Iterator[str]:
    server = build_core_server(
        build_core_tools(todoist=FakeTodoistReadClient([]), dropbox_root=storage_root),
        auth=StaticKeyVerifier(STATIC_KEY),
    )
    with running_core(server) as url:
        yield url


async def call_protocol_make(url: str, arguments: dict[str, Any]) -> Any:
    headers = {"Authorization": f"Bearer {STATIC_KEY}"}
    async with (
        httpx2.AsyncClient(headers=headers) as http_client,
        streamable_http_client(url, http_client=http_client) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        return await session.call_tool("protocol_make", arguments)


def make_protocol(url: str, storage_root: Path, arguments: dict[str, Any]) -> str:
    result = anyio.run(call_protocol_make, url, arguments)
    assert not result.is_error, result.content[0].text
    paths = json.loads(result.content[0].text)
    assert paths["pdf_path"].startswith(f"{RECORDINGS}/")
    assert paths["typ_path"].startswith(f"{RECORDINGS}/")
    assert (storage_root / paths["typ_path"]).read_text("utf-8").startswith("#import")
    pdf = PdfReader(BytesIO((storage_root / paths["pdf_path"]).read_bytes()))
    return " ".join(" ".join((page.extract_text() or "").split()) for page in pdf.pages)


def test_meeting_protocol_lands_in_recordings_with_all_sections(
    core_url: str, storage_root: Path
):
    text = make_protocol(core_url, storage_root, MEETING)

    for section in (
        "Протокол встречи",
        "Участники",
        "Повестка",
        "Обсуждение",
        "Решения",
        "Поручения",
        "Открытые вопросы",
    ):
        assert section in text
    assert ACTION in text
    assert LITERAL_LINE in text


def test_call_protocol_has_no_agenda_and_keeps_markup_literal(
    core_url: str, storage_root: Path
):
    text = make_protocol(core_url, storage_root, CALL)

    for section in ("Протокол звонка", "Стороны", "Договорённости", "Поручения"):
        assert section in text
    assert "Повестка" not in text
    assert "Обсуждение" not in text
    assert ACTION in text
    assert LITERAL_LINE in text


def test_call_with_agenda_is_tool_error(core_url: str):
    result = anyio.run(
        call_protocol_make, core_url, {**CALL, "agenda": ["Лишняя повестка"]}
    )

    assert result.is_error
    assert "повестки" in result.content[0].text
