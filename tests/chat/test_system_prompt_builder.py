from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.chat.actions.system_prompt_builder import SystemPromptBuilder

SYSTEM_PROMPT = Path(__file__).parents[2] / "data" / "system_prompt.txt"
TIMEZONE = ZoneInfo("Asia/Almaty")
ALL_CONNECTORS = ("tasks", "gmail", "whatsapp", "telegram", "scheduler")


def _prompt(connectors: tuple[str, ...]) -> str:
    return SystemPromptBuilder(
        template=SYSTEM_PROMPT.read_text(encoding="utf-8"),
        timezone=TIMEZONE,
        connectors=connectors,
    ).build()


def test_prompt_without_connectors_keeps_cases_and_drops_connector_sections() -> None:
    prompt = _prompt(())

    assert "## Кейсы" in prompt
    assert "task_add" in prompt
    for absent in (
        "## Задачник",
        "find_tasks",
        "read_task",
        "task_link",
        "search_mail",
        "draft_mail",
        "WhatsApp",
        "search_whatsapp",
        "## Расписания",
        "schedule_",
        "<!--",
    ):
        assert absent not in prompt


def test_prompt_with_task_manager_has_its_section_only() -> None:
    prompt = _prompt(("tasks",))

    assert "## Задачник" in prompt
    assert "find_tasks" in prompt
    assert "task_link" in prompt
    assert "search_mail" not in prompt
    assert "search_whatsapp" not in prompt
    assert "<!--" not in prompt


def test_prompt_with_scheduler_has_its_section_only() -> None:
    prompt = _prompt(("scheduler",))

    assert "## Расписания" in prompt
    for tool in ("schedule_add", "schedule_list", "schedule_cancel"):
        assert tool in prompt
    assert "1#1" in prompt
    assert "find_tasks" not in prompt
    assert "<!--" not in prompt


@pytest.mark.parametrize("connectors", [(), ALL_CONNECTORS])
def test_prompt_placeholders_are_filled(connectors: tuple[str, ...]) -> None:
    prompt = _prompt(connectors)

    for placeholder in ("{today}", "{now}", "{timezone}"):
        assert placeholder not in prompt
    assert "Asia/Almaty" in prompt


def test_prompt_never_names_removed_task_tools() -> None:
    template = SYSTEM_PROMPT.read_text(encoding="utf-8")

    for removed in ("create_task", "update_task", "add_task_link", "task_link_todoist"):
        assert removed not in template


def test_prompt_never_names_the_task_manager_implementation() -> None:
    template = SYSTEM_PROMPT.read_text(encoding="utf-8")

    assert "todoist" not in template.casefold()


def test_dropped_section_leaves_no_blank_line_run() -> None:
    template = (
        "до\n\n<!-- connector:gmail -->\n## Почта\n\nтекст\n<!-- /connector:gmail -->\n\n"
        "после\n"
    )

    prompt = SystemPromptBuilder(template=template, timezone=TIMEZONE).build()

    assert prompt == "до\n\nпосле\n"
