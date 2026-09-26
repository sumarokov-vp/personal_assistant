from datetime import date, datetime
from typing import ClassVar
from zoneinfo import ZoneInfo

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, Field

from src.ai_tools.memory_common import MEMORY_ERRORS, error_reply, success_reply
from src.ai_tools.memory_upsert_deadline.protocols.i_deadline_store import (
    IDeadlineStore,
)
from src.memory.models import Deadline

KEEP_PREVIOUS = "Не передавай, если не знаешь: у существующей записи останется прежнее."


class MemoryUpsertDeadlineInput(BaseModel):
    what: str = Field(
        description=(
            "Что истекает: вид документа или услуги («Паспорт РФ», «ЭЦП РК», "
            "«Страховка авто»). Без номеров документов и реквизитов."
        ),
    )
    whose: str = Field(description="Чьё: имя члена семьи, например «Владимир».")
    expires: date = Field(description="Новая дата окончания срока, YYYY-MM-DD.")
    renewal: str | None = Field(
        default=None, description=f"Где и как продлевать. {KEEP_PREVIOUS}"
    )
    duration: str | None = Field(
        default=None, description=f"Сколько занимает продление. {KEEP_PREVIOUS}"
    )
    source: str | None = Field(
        default=None,
        description=f"Откуда факт: путь в Dropbox, тема письма или «диалог». {KEEP_PREVIOUS}",
    )


class MemoryUpsertDeadlineTool(BaseTool):
    name: ClassVar[str] = "memory_upsert_deadline"
    description: ClassVar[str] = (
        "Добавляет или обновляет строку реестра сроков (документы семьи и всё истекающее). "
        "Строка ищется по паре «Что» + «Чьё» без учёта регистра: совпала — обновляется, "
        "нет — добавляется. Вызывай сразу, как владелец сообщил новый срок "
        "(«продлил паспорт, новый до …»). Для обновления бери «Что» и «Чьё» "
        "из memory_show, чтобы не завести дубль."
    )

    Input: ClassVar[type[BaseModel]] = MemoryUpsertDeadlineInput

    def __init__(self, deadlines: IDeadlineStore, timezone: ZoneInfo) -> None:
        self._deadlines = deadlines
        self._timezone = timezone

    def execute(self, input: MemoryUpsertDeadlineInput, context: ToolContext) -> str:
        try:
            existing = self._deadlines.find(input.what, input.whose)
            deadline = Deadline.model_validate(
                {
                    **(existing.model_dump() if existing else {}),
                    **input.model_dump(exclude_none=True),
                    "updated": datetime.now(tz=self._timezone).date(),
                }
            )
            outcome = self._deadlines.upsert(deadline)
        except MEMORY_ERRORS as error:
            return error_reply(self._deadlines.path, error)
        return success_reply(outcome.value, self._deadlines.path, deadline)
