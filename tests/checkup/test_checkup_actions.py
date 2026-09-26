import json
from typing import Any

import pytest
from ai_framework.entities.tool_context import ToolContext

from src.ai_tools.checkup_create_task.checkup_run_missing_error import (
    CheckupRunMissingError,
)
from src.ai_tools.checkup_create_task.tool import (
    CheckupCreateTaskInput,
    CheckupCreateTaskTool,
)
from src.ai_tools.checkup_skip.tool import CheckupSkipInput, CheckupSkipTool
from src.checkup.models.checkup_key import CheckupKey
from src.checkup.repos.checkup_journal_page_format import CheckupJournalPageFormat
from src.checkup.services.checkup_actions.checkup_key_error import CheckupKeyError
from src.checkup.services.entities.checkup_run import CheckupRun
from src.memory.repos.memory_page_format_error import MemoryPageFormatError
from tests.checkup.fakes import FakeTodoistClient, InMemoryWiki

JOURNAL = CheckupJournalPageFormat.path
KEY = "ЭЦП РК | Владимир | 20.11.2026"


def create(
    tool: CheckupCreateTaskTool, run: CheckupRun, key: str = KEY
) -> dict[str, Any]:
    payload = CheckupCreateTaskInput(
        key=key,
        content="Продлить ЭЦП РК",
        due="2026-11-05",
        reason="ЭЦП истекает 20.11.2026, продление только в РК, вылет 12.11.2026",
    )
    return json.loads(tool.execute(payload, ToolContext(run.as_tool_context())))


def skip(tool: CheckupSkipTool, key: str = KEY) -> dict[str, Any]:
    payload = CheckupSkipInput(key=key, reason="есть задача владельца «ЭЦП»")
    return json.loads(tool.execute(payload, ToolContext()))


def journal_rows(wiki: InMemoryWiki) -> list[str]:
    lines = wiki.files[JOURNAL].splitlines()
    header = lines.index("| Ключ | Когда | Что сделано | Задача Todoist | Причина |")
    return [line for line in lines[header + 2 :] if line.startswith("|")]


def test_first_create_makes_one_task_and_one_journal_row(
    create_tool: CheckupCreateTaskTool,
    wiki: InMemoryWiki,
    todoist: FakeTodoistClient,
):
    run = CheckupRun()

    answer = create(create_tool, run)

    assert answer["status"] == "created"
    assert len(todoist.added) == 1
    assert todoist.added_labels == [["pa"]]
    rows = journal_rows(wiki)
    assert len(rows) == 1
    assert "26.09.2026" in rows[0]
    assert "app.todoist.com/app/task/task-1" in rows[0]
    assert wiki.files[JOURNAL].startswith("Ведёт ассистент")
    assert [task.content for task in run.created] == ["Продлить ЭЦП РК"]
    assert run.created[0].due == "2026-11-05"
    assert run.created[0].reason.startswith("ЭЦП истекает")


def test_repeat_with_differently_written_key_does_nothing(
    create_tool: CheckupCreateTaskTool,
    wiki: InMemoryWiki,
    todoist: FakeTodoistClient,
):
    create(create_tool, CheckupRun())
    second_run = CheckupRun()

    answer = create(create_tool, second_run, key="  эцп   рк |ВЛАДИМИР|  20.11.2026 ")

    assert answer["status"] == "already_done"
    assert len(todoist.added) == 1
    assert len(journal_rows(wiki)) == 1
    assert second_run.created == []


def test_key_date_is_normalized(
    create_tool: CheckupCreateTaskTool, todoist: FakeTodoistClient
):
    create(create_tool, CheckupRun())

    answer = create(create_tool, CheckupRun(), key="ЭЦП РК | Владимир | 2026-11-20")

    assert answer["status"] == "already_done"
    assert len(todoist.added) == 1


def test_renewed_document_gets_new_key(
    create_tool: CheckupCreateTaskTool, todoist: FakeTodoistClient
):
    create(create_tool, CheckupRun())

    answer = create(create_tool, CheckupRun(), key="ЭЦП РК | Владимир | 20.11.2027")

    assert answer["status"] == "created"
    assert len(todoist.added) == 2


def test_skip_writes_row_without_task(
    skip_tool: CheckupSkipTool,
    create_tool: CheckupCreateTaskTool,
    wiki: InMemoryWiki,
    todoist: FakeTodoistClient,
):
    run = CheckupRun()

    answer = skip(skip_tool)

    assert answer["status"] == "skipped"
    assert todoist.added == []
    assert len(journal_rows(wiki)) == 1
    assert answer["journal"]["task"] == ""
    assert create(create_tool, run)["status"] == "already_done"
    assert todoist.added == []
    assert run.created == []


def test_malformed_key_creates_nothing(
    create_tool: CheckupCreateTaskTool,
    wiki: InMemoryWiki,
    todoist: FakeTodoistClient,
):
    with pytest.raises(CheckupKeyError):
        create(create_tool, CheckupRun(), key="ЭЦП РК · Владимир · 20.11.2026")

    assert todoist.added == []
    assert wiki.files == {}


def test_create_outside_checkup_run_is_refused(
    create_tool: CheckupCreateTaskTool, todoist: FakeTodoistClient
):
    payload = CheckupCreateTaskInput(key=KEY, content="x", due="завтра", reason="y")

    with pytest.raises(CheckupRunMissingError):
        create_tool.execute(payload, ToolContext({"chat_id": 1}))

    assert todoist.added == []


def test_broken_journal_page_blocks_task_creation(
    create_tool: CheckupCreateTaskTool,
    wiki: InMemoryWiki,
    todoist: FakeTodoistClient,
):
    wiki.files[JOURNAL] = "| Ключ | Дата | Что сделано |\n| --- | --- | --- |\n"

    with pytest.raises(MemoryPageFormatError):
        create(create_tool, CheckupRun())

    assert todoist.added == []


@pytest.mark.parametrize(
    "raw",
    ["ЭЦП | Владимир", "ЭЦП | Владимир | 31.11.2026", " | Владимир | 20.11.2026"],
)
def test_key_rejects_malformed(raw: str):
    assert CheckupKey.parse(raw) is None


def test_key_accepts_short_day_and_month():
    key = CheckupKey.parse("ЭЦП РК | Владимир | 5.1.2027")

    assert key is not None
    assert key.text == "ЭЦП РК | Владимир | 05.01.2027"
