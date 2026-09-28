import json
from datetime import UTC, datetime
from typing import ClassVar, Literal
from zoneinfo import ZoneInfo

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.case_add_event.protocols.i_case_event_adder import ICaseEventAdder
from src.cases.errors.cases_service_error import CasesServiceError
from src.cases.models.case_source import CaseSource
from src.cases.models.new_event import NewEvent


class CaseAddEventInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    case_id: str = Field(min_length=1)
    source: CaseSource = Field(
        description="Откуда событие: owner — сам владелец в чате, gmail, whatsapp, "
        "todoist, dropbox, wiki, assistant — вывод ассистента"
    )
    kind: Literal["note", "message", "file", "link"] = Field(
        description="note — реплика или заметка, message — письмо или сообщение, "
        "file — файл, link — ссылка. Задачи — не этим инструментом"
    )
    source_ref: str | None = Field(
        default=None,
        description="id события в источнике: id письма Gmail, id сообщения WhatsApp, путь "
        "Dropbox или вики. Повтор того же source_ref в деле новую запись не даёт",
    )
    url: str | None = Field(default=None, description="Ссылка на оригинал, если есть")
    occurred_at: datetime | None = Field(
        default=None,
        description="Когда это случилось: YYYY-MM-DDTHH:MM, без пояса — пояс владельца. "
        "Не передано — сейчас",
    )
    summary: str = Field(
        min_length=1,
        description="Коротко, что произошло и что это значит для дела. Не копия письма",
    )


class CaseAddEventTool(BaseTool):
    name: ClassVar[str] = "case_add_event"
    description: ClassVar[str] = (
        "Записывает в ленту дела одно событие: реплику владельца, письмо, сообщение, файл "
        "или ссылку. Привязывается конкретное событие, не собеседник; одно событие — одно "
        "дело. В ленте хранится пересказ и ссылка на источник, оригинал остаётся там."
    )
    Input: ClassVar[type[BaseModel]] = CaseAddEventInput

    def __init__(self, adder: ICaseEventAdder, timezone: ZoneInfo) -> None:
        self._adder = adder
        self._timezone = timezone

    def execute(self, input: CaseAddEventInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        event = NewEvent(
            occurred_at=self._aware(input.occurred_at),
            source=input.source,
            kind=input.kind,
            source_ref=input.source_ref or None,
            url=input.url or None,
            summary=input.summary,
        )
        try:
            addition = self._adder.add_event(input.case_id, event)
        except CasesServiceError as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)
        if addition.created:
            return f"Событие записано в дело: {addition.event.id}"
        return f"Это событие уже есть в ленте дела: {addition.event.id}"

    def _aware(self, moment: datetime | None) -> datetime:
        if moment is None:
            return datetime.now(UTC)
        if moment.tzinfo is None:
            return moment.replace(tzinfo=self._timezone)
        return moment
