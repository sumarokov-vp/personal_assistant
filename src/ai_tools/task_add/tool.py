import json
from datetime import UTC, date, datetime
from typing import ClassVar, Literal
from zoneinfo import ZoneInfo

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.task_add.protocols.i_task_event_adder import ITaskEventAdder
from src.ai_tools.task_add.protocols.i_task_recorded_listener import (
    ITaskRecordedListener,
)
from src.ai_tools.task_add.task_assignee import ASSIGNEE_HINT, is_known_assignee
from src.cases.errors.cases_service_error import CasesServiceError
from src.cases.models.new_event import NewEvent
from src.cases.models.new_task import NewTask

INBOX_CASE_ID = "inbox"


class TaskAddInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    case_id: str | None = Field(
        default=None,
        description="Дело, к которому относится задача. Не относится ни к какому — не "
        "передавай: задача ляжет в служебное дело «Без темы»",
    )
    summary: str = Field(
        min_length=1,
        description="Что сделать и зачем: «Получить справку в консульстве — нужна для "
        "РВП бизнес-мигранта»",
    )
    assignee: str = Field(
        default="self",
        description="Кто делает: self — сам владелец, assistant — ассистент, "
        "agent:<имя>, person:<имя>, colleague:<пользователь>. Исполнитель только "
        "записывается — поручения никому не уходят",
    )
    due: date | None = Field(
        default=None,
        description="Срок — жёсткая внешняя граница (дедлайн), YYYY-MM-DD; не «когда "
        "займусь». Нет границы — не передавай",
    )
    occurred_at: datetime | None = Field(
        default=None,
        description="Когда поставлена: YYYY-MM-DDTHH:MM, без пояса — пояс владельца. "
        "Не передано — сейчас",
    )
    source: Literal["owner", "assistant"] = Field(
        default="owner",
        description="owner — владелец попросил, assistant — ассистент поставил сам",
    )


class TaskAddTool(BaseTool):
    name: ClassVar[str] = "task_add"
    description: ClassVar[str] = (
        "Ставит задачу — шаг внутри дела — событием в ленту дела: что сделать и зачем, "
        "исполнитель, срок-дедлайн. Дело на каждую задачу не заводи: задача без темы "
        "идёт без case_id в служебное дело «Без темы»."
    )
    Input: ClassVar[type[BaseModel]] = TaskAddInput

    def __init__(
        self,
        adder: ITaskEventAdder,
        timezone: ZoneInfo,
        listener: ITaskRecordedListener | None = None,
    ) -> None:
        self._adder = adder
        self._timezone = timezone
        self._listener = listener

    def execute(self, input: TaskAddInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        if not is_known_assignee(input.assignee):
            return _error(
                f"Неизвестный исполнитель «{input.assignee}». {ASSIGNEE_HINT}"
            )
        case_id = input.case_id or INBOX_CASE_ID
        event = NewEvent(
            occurred_at=self._aware(input.occurred_at),
            source=input.source,
            kind="task",
            summary=input.summary,
            task=NewTask(due=input.due, assignee=input.assignee),
        )
        try:
            addition = self._adder.add_event(case_id, event)
        except CasesServiceError as error:
            return _error(str(error))
        if self._listener is not None:
            self._listener.task_recorded(case_id, addition.event)
        due = input.due.strftime("%d.%m.%Y") if input.due else "без срока"
        return (
            f"Задача записана: {addition.event.id} · срок {due} · "
            f"исполнитель {input.assignee}"
        )

    def _aware(self, moment: datetime | None) -> datetime:
        if moment is None:
            return datetime.now(UTC)
        if moment.tzinfo is None:
            return moment.replace(tzinfo=self._timezone)
        return moment


def _error(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)
