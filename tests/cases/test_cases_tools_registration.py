from typing import Any
from unittest.mock import Mock

import pytest

from workers.bot import __main__ as bot_main


class ToolsCaptured(Exception):  # noqa: N818
    def __init__(self, tools: list[Any]) -> None:
        super().__init__("tools captured")
        self.names = [tool.name for tool in tools]


def capture_tools(**kwargs: Any) -> None:
    raise ToolsCaptured(kwargs["tools"])


@pytest.fixture
def bot_start(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bot_main, "load_dotenv", Mock())
    monkeypatch.setattr(bot_main, "BotApplication", Mock())
    monkeypatch.setattr(bot_main, "admit_only_owner", Mock())
    monkeypatch.setattr(bot_main, "build_attachment_store", Mock())
    monkeypatch.setattr(bot_main, "start_sweeper", Mock())
    monkeypatch.setattr(bot_main, "build_chat_attachments", Mock())
    monkeypatch.setattr(bot_main, "build_configured_wiki_factory", Mock())
    monkeypatch.setattr(bot_main, "build_wiki_tools", Mock(return_value=[]))
    monkeypatch.setattr(bot_main, "build_memory_tools", Mock(return_value=[]))
    monkeypatch.setattr(bot_main, "AIApplication", capture_tools)
    for name, value in {
        "OWNER_TELEGRAM_ID": "1",
        "BOT_TOKEN": "1:test",
        "BOT_DB_URL": "postgres://unused",
        "REDIS_URL": "redis://unused",
        "AI_DB_URL": "postgres://unused",
        "AI_MODEL": "unused",
    }.items():
        monkeypatch.setenv(name, value)
    for name in (
        "TODOIST_TOKEN",
        "GMAIL_CLIENT_ID",
        "GMAIL_CLIENT_SECRET",
        "GMAIL_REFRESH_TOKEN",
        "WHATSAPP_MACOS_SNAPSHOT_DIR",
        "DROPBOX_ROOT",
        "CASES_API_URL",
        "CASES_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.usefixtures("bot_start")
def test_cases_tools_registered_without_todoist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CASES_API_URL", "http://cases.test")
    monkeypatch.setenv("CASES_API_KEY", "key")

    with pytest.raises(ToolsCaptured) as captured:
        bot_main.main()

    names = captured.value.names
    assert {
        "case_find",
        "case_open",
        "case_read",
        "case_add_event",
        "case_update",
    } <= set(names)
    assert "find_tasks" not in names


@pytest.mark.usefixtures("bot_start")
def test_no_cases_tools_without_cases_variables() -> None:
    with pytest.raises(ToolsCaptured) as captured:
        bot_main.main()

    assert not [name for name in captured.value.names if name.startswith("case_")]


@pytest.mark.usefixtures("bot_start")
@pytest.mark.parametrize(
    ("present", "missing"),
    [("CASES_API_URL", "CASES_API_KEY"), ("CASES_API_KEY", "CASES_API_URL")],
)
def test_bot_fails_on_start_with_only_one_cases_variable(
    monkeypatch: pytest.MonkeyPatch, present: str, missing: str
) -> None:
    monkeypatch.setenv(present, "value")

    with pytest.raises(ValueError, match=missing):
        bot_main.main()
