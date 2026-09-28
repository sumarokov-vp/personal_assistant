import json
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from ai_framework import ToolContext

from src.ai_tools.case_add_event import CaseAddEventTool
from src.ai_tools.case_add_event.tool import CaseAddEventInput
from src.ai_tools.case_find import CaseFindTool
from src.ai_tools.case_find.tool import CaseFindInput
from src.ai_tools.case_open import CaseOpenTool
from src.ai_tools.case_open.tool import CaseOpenInput
from src.ai_tools.case_read import CaseReadTool
from src.ai_tools.case_read.tool import CaseReadInput
from src.ai_tools.case_update import CaseUpdateTool
from src.ai_tools.case_update.tool import CaseUpdateInput
from src.cases.repos.cases_http_client import CasesHttpClient
from src.cases.services.untrusted_frame.untrusted_case_frame import UntrustedCaseFrame
from tests.cases.conftest import (
    CASE_ID,
    TASK_ID,
    FakeCasesService,
    case_payload,
    event_payload,
)

ALMATY = ZoneInfo("Asia/Almaty")
CONTEXT = ToolContext({})
CASE_PATH = f"/api/v1/cases/{CASE_ID}"


def read_tool(client: CasesHttpClient) -> CaseReadTool:
    return CaseReadTool(reader=client, frame=UntrustedCaseFrame(), timezone=ALMATY)


def test_case_read_lists_feed_by_occurred_at_in_owner_timezone(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    late_note = event_payload(
        id="e2",
        occurred_at="2026-09-28T06:30:00Z",
        source="gmail",
        kind="message",
        source_ref="18c2f",
        url="https://mail.google.com/mail/u/0/#all/18c2f",
        summary="Нотариус прислал список документов",
    )
    task = event_payload(
        id=TASK_ID,
        occurred_at="2026-09-27T19:15:00Z",
        kind="task",
        summary="Получить справку в консульстве — для РВП",
        task={
            "status": "open",
            "due": "2026-10-20",
            "assignee": "self",
            "external_id": None,
            "closed_at": None,
        },
    )
    fake_service.on(
        "GET",
        CASE_PATH,
        200,
        {"case": case_payload(), "events": [late_note, task], "has_earlier": False},
    )

    text = read_tool(client).execute(CaseReadInput(case_id=CASE_ID), CONTEXT)

    lines = text.splitlines()
    task_line = next(line for line in lines if TASK_ID in line)
    mail_line = next(line for line in lines if "Нотариус" in line)
    assert lines.index(task_line) < lines.index(mail_line)
    assert task_line.startswith("28.09.2026 00:15 · owner · задача")
    assert "open, срок 20.10.2026, исполнитель self" in task_line
    assert mail_line == (
        "28.09.2026 11:30 · gmail · message: Нотариус прислал список документов · "
        "https://mail.google.com/mail/u/0/#all/18c2f"
    )
    assert "<untrusted_case" in text


def test_case_read_of_missing_case_is_model_error(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on("GET", CASE_PATH, 404, {"error": "case_not_found"})

    result = json.loads(
        read_tool(client).execute(CaseReadInput(case_id=CASE_ID), CONTEXT)
    )

    assert result["error"].startswith("Кейс не найден")


def test_unreachable_service_is_model_error_not_exception(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.fail("GET", "/api/v1/cases", httpx.ConnectError("refused"))
    fake_service.fail("POST", "/api/v1/cases", httpx.ReadTimeout("slow"))
    find = CaseFindTool(finder=client, frame=UntrustedCaseFrame(), timezone=ALMATY)
    open_case = CaseOpenTool(opener=client)

    found = json.loads(find.execute(CaseFindInput(q="ТОО"), CONTEXT))
    opened = json.loads(
        open_case.execute(CaseOpenInput(title="ТОО", summary="Своё ТОО"), CONTEXT)
    )

    assert "недоступен" in found["error"]
    assert "недоступен" in opened["error"]


def test_case_add_event_reads_naive_time_in_owner_timezone(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    fake_service.on("POST", f"{CASE_PATH}/events", 201, event_payload())
    tool = CaseAddEventTool(adder=client, timezone=ALMATY)

    result = tool.execute(
        CaseAddEventInput(
            case_id=CASE_ID,
            source="owner",
            kind="note",
            occurred_at=datetime(2026, 9, 28, 11, 0),  # noqa: DTZ001
            summary="Справку из поликлиники забрал",
        ),
        CONTEXT,
    )

    assert fake_service.last_body() == {
        "occurred_at": "2026-09-28T11:00:00+05:00",
        "source": "owner",
        "kind": "note",
        "summary": "Справку из поликлиники забрал",
    }
    assert result.startswith("Событие записано")


def test_case_update_without_changes_sends_nothing(
    client: CasesHttpClient, fake_service: FakeCasesService
) -> None:
    result = json.loads(
        CaseUpdateTool(updater=client).execute(
            CaseUpdateInput(case_id=CASE_ID), CONTEXT
        )
    )

    assert "Нечего менять" in result["error"]
    assert fake_service.requests == []
