from typing import Any
from unittest.mock import Mock

import pytest

from workers.bot import __main__ as bot_main

SCHEDULE_TOOLS = {"schedule_add", "schedule_list", "schedule_cancel"}


class StartCaptured(Exception):  # noqa: N818
    def __init__(self, tools: list[Any], system_prompt: str) -> None:
        super().__init__("start captured")
        self.names = {tool.name for tool in tools}
        self.system_prompt = system_prompt


def capture_start(**kwargs: Any) -> None:
    raise StartCaptured(kwargs["tools"], kwargs["system_prompt"])


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
    monkeypatch.setattr(bot_main, "AIApplication", capture_start)
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
        "TELEGRAM_USER_SECRETS_FILE",
        "DROPBOX_ROOT",
        "CASES_API_URL",
        "CASES_API_KEY",
        "SCHEDULER_API_URL",
        "SCHEDULER_API_KEY",
        "SCHEDULER_AMQP_URL",
        "SCHEDULER_QUEUE",
        "ASSISTANT_MAIL_URL",
        "ASSISTANT_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.usefixtures("bot_start")
def test_schedule_tools_and_prompt_section_with_scheduler_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCHEDULER_API_URL", "http://scheduler.test")
    monkeypatch.setenv("SCHEDULER_API_KEY", "key")

    with pytest.raises(StartCaptured) as captured:
        bot_main.main()

    assert captured.value.names >= SCHEDULE_TOOLS
    assert "## Расписания" in captured.value.system_prompt


@pytest.mark.usefixtures("bot_start")
def test_no_schedule_tools_nor_prompt_section_without_scheduler_variables() -> None:
    with pytest.raises(StartCaptured) as captured:
        bot_main.main()

    assert not captured.value.names & SCHEDULE_TOOLS
    assert "## Расписания" not in captured.value.system_prompt
    assert "schedule_" not in captured.value.system_prompt


@pytest.mark.usefixtures("bot_start")
@pytest.mark.parametrize(
    ("present", "missing"),
    [
        ("SCHEDULER_API_URL", "SCHEDULER_API_KEY"),
        ("SCHEDULER_API_KEY", "SCHEDULER_API_URL"),
    ],
)
def test_bot_fails_on_start_with_only_one_scheduler_variable(
    monkeypatch: pytest.MonkeyPatch, present: str, missing: str
) -> None:
    monkeypatch.setenv(present, "value")

    with pytest.raises(ValueError, match=missing):
        bot_main.main()
