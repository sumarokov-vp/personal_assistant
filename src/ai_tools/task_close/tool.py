import json
from datetime import UTC, datetime
from typing import ClassVar, Literal
from zoneinfo import ZoneInfo

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.task_close.protocols.i_task_closed_listener import (
    ITaskClosedListener,
)
from src.ai_tools.task_close.protocols.i_task_closer import ITaskCloser
from src.cases.errors.cases_service_error import CasesServiceError
from src.cases.models.task_closure import TaskClosure


class TaskCloseInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    task_id: str = Field(min_length=1)
    status: Literal["done", "cancelled"] = Field(
        description="done — сделана, cancelled — отменена, больше не нужна"
    )
    summary: str | None = Field(
        default=None,
        min_length=1,
        description="Чем кончилось: «справку получил», «РВП больше не нужен»",
    )
    occurred_at: datetime | None = Field(
        default=None,
        description="Когда: YYYY-MM-DDTHH:MM, без пояса — пояс владельца. Не передано — "
        "сейчас",
    )
    source: Literal["owner", "assistant"] = Field(
        default="owner",
        description="owner — владелец сказал, assistant — ассистент увидел сам",
    )


class TaskCloseTool(BaseTool):
    name: ClassVar[str] = "task_close"
    description: ClassVar[str] = (
        "Закрывает задачу: done — сделана, cancelled — отменена. В ленту кейса ложится "
        "событие закрытия; уже закрытая задача второго события не даёт."
    )
    Input: ClassVar[type[BaseModel]] = TaskCloseInput

    def __init__(
        self,
        closer: ITaskCloser,
        timezone: ZoneInfo,
        listener: ITaskClosedListener | None = None,
    ) -> None:
        self._closer = closer
        self._timezone = timezone
        self._listener = listener

    def execute(self, input: TaskCloseInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        closure = TaskClosure(
            status=input.status,
            occurred_at=self._aware(input.occurred_at),
            source=input.source,
            summary=input.summary,
        )
        try:
            task = self._closer.close_task(input.task_id, closure)
        except CasesServiceError as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)
        if self._listener is not None:
            self._listener.task_closed(task)
        return f"Задача закрыта: {task.id} · {task.status} · {task.summary}"

    def _aware(self, moment: datetime | None) -> datetime:
        if moment is None:
            return datetime.now(UTC)
        if moment.tzinfo is None:
            return moment.replace(tzinfo=self._timezone)
        return moment
