from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.chat.actions.system_prompt_builder import SystemPromptBuilder

SYSTEM_PROMPT = Path(__file__).parents[2] / "data" / "system_prompt.txt"
TIMEZONE = ZoneInfo("Asia/Almaty")
ALL_CONNECTORS = ("todoist", "gmail", "whatsapp")


def _prompt(connectors: tuple[str, ...]) -> str:
    return SystemPromptBuilder(
        template=SYSTEM_PROMPT.read_text(encoding="utf-8"),
        timezone=TIMEZONE,
        connectors=connectors,
    ).build()


def test_prompt_without_connectors_keeps_cases_and_drops_connector_sections() -> None:
    prompt = _prompt(())

    assert "## Дела" in prompt
    assert "task_add" in prompt
    for absent in (
        "Todoist",
        "find_tasks",
        "task_link_todoist",
        "search_mail",
        "draft_mail",
        "WhatsApp",
        "search_whatsapp",
        "<!--",
    ):
        assert absent not in prompt


def test_prompt_with_todoist_has_its_section_only() -> None:
    prompt = _prompt(("todoist",))

    assert "## Задачи Todoist" in prompt
    assert "find_tasks" in prompt
    assert "task_link_todoist" in prompt
    assert "search_mail" not in prompt
    assert "search_whatsapp" not in prompt
    assert "<!--" not in prompt


@pytest.mark.parametrize("connectors", [(), ALL_CONNECTORS])
def test_prompt_placeholders_are_filled(connectors: tuple[str, ...]) -> None:
    prompt = _prompt(connectors)

    for placeholder in ("{today}", "{now}", "{timezone}"):
        assert placeholder not in prompt
    assert "Asia/Almaty" in prompt


def test_prompt_never_names_unregistered_todoist_tools() -> None:
    template = SYSTEM_PROMPT.read_text(encoding="utf-8")

    for removed in ("create_task", "update_task", "add_task_link"):
        assert removed not in template


def test_dropped_section_leaves_no_blank_line_run() -> None:
    template = (
        "до\n\n<!-- connector:gmail -->\n## Почта\n\nтекст\n<!-- /connector:gmail -->\n\n"
        "после\n"
    )

    prompt = SystemPromptBuilder(template=template, timezone=TIMEZONE).build()

    assert prompt == "до\n\nпосле\n"
