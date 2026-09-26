from datetime import date
from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, Field

from src.ai_tools.memory_common import MEMORY_ERRORS, error_reply, success_reply
from src.ai_tools.memory_upsert_trip.protocols.i_whereabouts_store import (
    IWhereaboutsStore,
)
from src.memory.models import Whereabouts

KEEP_PREVIOUS = "Не передавай, если не знаешь: у существующей записи останется прежнее."


class MemoryUpsertTripInput(BaseModel):
    since: date = Field(description="С какой даты владелец там, YYYY-MM-DD.")
    place: str = Field(description="Где: город или страна, например «Чиангмай».")
    until: date | None = Field(
        default=None, description=f"По какую дату, YYYY-MM-DD. {KEEP_PREVIOUS}"
    )
    purpose: str | None = Field(
        default=None,
        description=f"Что за поездка: отпуск, зимовка, командировка. {KEEP_PREVIOUS}",
    )
    source: str | None = Field(
        default=None,
        description=f"Откуда факт: тема письма, путь в Dropbox или «диалог». {KEEP_PREVIOUS}",
    )


class MemoryUpsertTripTool(BaseTool):
    name: ClassVar[str] = "memory_upsert_trip"
    description: ClassVar[str] = (
        "Добавляет или обновляет строку таймлайна «Где я буду» (поездки и переезды владельца). "
        "Строка ищется по паре «С» + «Где»: совпала — обновляется, нет — добавляется. "
        "Вызывай, как только владелец назвал поездку или её даты («лечу в Чиангмай 12.11»). "
        "Если сдвинулась дата начала — сначала посмотри memory_show: новая «С» заведёт новую строку."
    )

    Input: ClassVar[type[BaseModel]] = MemoryUpsertTripInput

    def __init__(self, whereabouts: IWhereaboutsStore) -> None:
        self._whereabouts = whereabouts

    def execute(self, input: MemoryUpsertTripInput, context: ToolContext) -> str:
        try:
            existing = self._whereabouts.find(input.since, input.place)
            trip = Whereabouts.model_validate(
                {
                    **(existing.model_dump() if existing else {}),
                    **input.model_dump(exclude_none=True),
                }
            )
            outcome = self._whereabouts.upsert(trip)
        except MEMORY_ERRORS as error:
            return error_reply(self._whereabouts.path, error)
        return success_reply(outcome.value, self._whereabouts.path, trip)
