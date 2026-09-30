import json
from typing import Any

from ai_framework import BaseTool, ToolContext

from src.task_mirror.services.mirror_pass import MirrorPass
from tests.task_mirror.fakes import (
    TODOIST_TASK_ID,
    StatefulCasesService,
    StatefulTodoist,
    todoist_task,
)

CONTEXT = ToolContext({})
MIRRORED = f"todoist:{TODOIST_TASK_ID}"


def _run(tool: BaseTool, arguments: dict[str, Any]) -> str:
    result = tool.execute(tool.Input.model_validate(arguments), CONTEXT)
    assert isinstance(result, str)
    return result


def _body(request: Any) -> Any:
    return json.loads(request.content)


def test_self_task_goes_to_todoist_and_gets_external_id(
    mirrored_tools: dict[str, BaseTool],
    cases_service: StatefulCasesService,
    todoist_service: StatefulTodoist,
) -> None:
    _run(
        mirrored_tools["task_add"],
        {"summary": "Получить справку", "due": "2026-10-20"},
    )

    [created] = todoist_service.sent("POST", "/tasks")
    assert _body(created) == {
        "content": "Получить справку",
        "labels": ["pa"],
        "deadline_date": "2026-10-20",
    }
    [patch] = cases_service.sent("PATCH", "/tasks/task-1")
    assert _body(patch)["external_id"] == MIRRORED


def test_task_of_other_assignee_never_reaches_todoist(
    mirrored_tools: dict[str, BaseTool], todoist_service: StatefulTodoist
) -> None:
    _run(
        mirrored_tools["task_add"],
        {"summary": "Собрать выписки", "assignee": "agent:accountant"},
    )

    assert todoist_service.requests == []


def test_closing_our_task_does_not_close_it_in_todoist(
    mirrored_tools: dict[str, BaseTool],
    cases_service: StatefulCasesService,
    todoist_service: StatefulTodoist,
) -> None:
    cases_service.add_task("t1", external_id=MIRRORED)

    _run(mirrored_tools["task_close"], {"task_id": "t1", "status": "done"})

    assert todoist_service.requests == []
    assert cases_service.tasks["t1"]["status"] == "done"


def test_due_change_moves_todoist_deadline(
    mirrored_tools: dict[str, BaseTool],
    cases_service: StatefulCasesService,
    todoist_service: StatefulTodoist,
) -> None:
    cases_service.add_task("t1", external_id=MIRRORED)
    todoist_service.tasks[TODOIST_TASK_ID] = todoist_task(
        TODOIST_TASK_ID, "Получить справку", ["pa"]
    )

    _run(
        mirrored_tools["task_update"],
        {"task_id": "t1", "due": "2026-10-15", "summary": "нотариус перенёс"},
    )

    [update] = todoist_service.sent("POST", f"/tasks/{TODOIST_TASK_ID}")
    assert _body(update) == {"deadline_date": "2026-10-15"}


def test_todoist_down_does_not_break_task_add_and_next_pass_mirrors(
    mirrored_tools: dict[str, BaseTool],
    mirror_pass: MirrorPass,
    cases_service: StatefulCasesService,
    todoist_service: StatefulTodoist,
) -> None:
    todoist_service.down = True
    answer = _run(mirrored_tools["task_add"], {"summary": "Получить справку"})
    assert answer.startswith("Задача записана")
    assert cases_service.tasks["task-1"]["external_id"] is None

    todoist_service.down = False
    mirror_pass.run()

    assert cases_service.tasks["task-1"]["external_id"] == MIRRORED
    assert len(todoist_service.sent("POST", "/tasks")) == 1


def test_completed_in_todoist_closes_our_task_once(
    mirror_pass: MirrorPass,
    cases_service: StatefulCasesService,
    todoist_service: StatefulTodoist,
) -> None:
    cases_service.add_task("t1", external_id=MIRRORED)
    todoist_service.activity(501, "completed")

    mirror_pass.run()
    mirror_pass.run()

    [close] = cases_service.sent("POST", "/tasks/t1/close")
    assert _body(close) | {"occurred_at": None} == {
        "status": "done",
        "occurred_at": None,
        "source": "todoist",
        "source_ref": "todoist:activity:501",
        "summary": "Закрыта в Todoist",
    }
    assert len(cases_service.transitions) == 1


def test_uncompleted_reopens_and_deleted_cancels(
    mirror_pass: MirrorPass,
    cases_service: StatefulCasesService,
    todoist_service: StatefulTodoist,
) -> None:
    cases_service.add_task("t1", external_id=MIRRORED)
    todoist_service.activity(501, "completed")
    todoist_service.activity(502, "uncompleted")
    todoist_service.activity(503, "deleted")

    mirror_pass.run()

    assert [t["status"] for t in cases_service.transitions] == [
        "done",
        "open",
        "cancelled",
    ]
    assert cases_service.transitions[-1]["source_ref"] == "todoist:activity:503"


def test_deadline_change_in_todoist_patches_due_once(
    mirror_pass: MirrorPass,
    cases_service: StatefulCasesService,
    todoist_service: StatefulTodoist,
) -> None:
    cases_service.add_task("t1", external_id=MIRRORED, due="2026-10-20")
    todoist_service.activity(
        601,
        "updated",
        deadline={"date": "2026-10-25"},
        last_deadline={"date": "2026-10-20"},
    )
    todoist_service.activity(602, "updated", description="уточнил")

    mirror_pass.run()
    mirror_pass.run()

    [patch] = cases_service.sent("PATCH", "/tasks/t1")
    assert _body(patch)["due"] == "2026-10-25"
    assert _body(patch)["source"] == "todoist"


def test_activities_of_foreign_tasks_are_ignored(
    mirror_pass: MirrorPass,
    cases_service: StatefulCasesService,
    todoist_service: StatefulTodoist,
) -> None:
    cases_service.add_task("t1", external_id=MIRRORED, assignee="agent:accountant")
    todoist_service.activity(701, "completed")

    mirror_pass.run()

    assert cases_service.transitions == []


def test_owner_todoist_task_is_linked_to_case_once(
    mirrored_tools: dict[str, BaseTool],
    cases_service: StatefulCasesService,
    todoist_service: StatefulTodoist,
) -> None:
    todoist_service.tasks[TODOIST_TASK_ID] = todoist_task(
        TODOIST_TASK_ID, "Позвонить нотариусу", []
    ) | {"deadline": {"date": "2026-10-03"}}
    arguments = {"task_ref": MIRRORED, "case_id": "case-1"}

    first = _run(mirrored_tools["task_link"], arguments)
    second = _run(mirrored_tools["task_link"], arguments)

    [event] = cases_service.sent("POST", "/cases/case-1/events")
    assert _body(event)["task"] == {
        "due": "2026-10-03",
        "assignee": "self",
        "external_id": MIRRORED,
    }
    assert first == second
    assert todoist_service.sent("POST", "/tasks") == []
