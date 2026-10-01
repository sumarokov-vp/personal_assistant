import logging
from typing import ClassVar
from zoneinfo import ZoneInfo

import pytest
from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel

from src.cases.errors import CasesServiceUnavailableError
from src.cases.models.case_feed import CaseFeed
from workers.scheduled_run.cases_briefing import CasesBriefing
from workers.scheduled_run.run_tools import scheduled_run_tools
from workers.scheduled_run.scheduler_settings import read_scheduler_settings


def _tool(tool_name: str) -> BaseTool:
    class _Named(BaseTool):
        name: ClassVar[str] = tool_name
        description: ClassVar[str] = tool_name
        Input: ClassVar[type[BaseModel]] = BaseModel

        def execute(self, input: BaseModel, context: ToolContext) -> str:  # noqa: A002, ARG002
            return ""

    return _Named()


def test_scheduled_run_has_bot_tools_without_colleague_send_and_schedules():
    names = [
        "case_read",
        "case_add_event",
        "colleague_send",
        "colleagues",
        "draft_mail",
        "schedule_add",
        "schedule_list",
        "schedule_cancel",
        "task_add",
    ]

    kept = scheduled_run_tools(_tool(name) for name in names)

    assert [tool.name for tool in kept] == [
        "case_read",
        "case_add_event",
        "colleagues",
        "draft_mail",
        "task_add",
    ]


def test_without_settings_scheduled_runs_are_off(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    monkeypatch.delenv("SCHEDULER_AMQP_URL", raising=False)
    monkeypatch.delenv("SCHEDULER_QUEUE", raising=False)

    with caplog.at_level(logging.INFO):
        assert read_scheduler_settings() is None

    assert "scheduled runs are off" in caplog.text


def test_half_of_settings_fails_start(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(
        "SCHEDULER_AMQP_URL", "amqp://schedule-sumarokov:x@rabbitmq/assistant"
    )
    monkeypatch.delenv("SCHEDULER_QUEUE", raising=False)

    with pytest.raises(ValueError, match="required together"):
        read_scheduler_settings()


class _UnavailableCases:
    def read_case(self, case_id: str, events_limit: int) -> CaseFeed:
        raise CasesServiceUnavailableError("сервис кейсов недоступен")


def test_unread_case_does_not_stop_the_run():
    brief = CasesBriefing(_UnavailableCases(), ZoneInfo("Asia/Almaty")).brief("c-1")

    assert brief.title is None
    assert brief.text.startswith("Кейс не прочитан:")


class _BrokenFeedCases:
    def read_case(self, case_id: str, events_limit: int) -> CaseFeed:
        raise ValueError("ответ сервиса не по модели")


def test_case_read_failure_of_any_kind_does_not_stop_the_run():
    brief = CasesBriefing(_BrokenFeedCases(), ZoneInfo("Asia/Almaty")).brief("c-1")

    assert brief.title is None
    assert brief.text == "Кейс не прочитан: ValueError"
