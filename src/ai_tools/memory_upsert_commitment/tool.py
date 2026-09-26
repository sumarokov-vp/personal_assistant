from datetime import date
from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, Field

from src.ai_tools.memory_common import MEMORY_ERRORS, error_reply, success_reply
from src.ai_tools.memory_upsert_commitment.protocols.i_commitment_store import (
    ICommitmentStore,
)
from src.memory.models import Commitment, CommitmentStatus

KEEP_PREVIOUS = "Не передавай, если не знаешь: у существующей записи останется прежнее."


class MemoryUpsertCommitmentInput(BaseModel):
    what: str = Field(description="Что обещано или чего ждём: «Прислать акт сверки».")
    parties: str = Field(
        description="Кто кому, например «я → бухгалтер» или «банк → я».",
    )
    due: date | None = Field(
        default=None, description=f"Срок, YYYY-MM-DD. {KEEP_PREVIOUS}"
    )
    status: CommitmentStatus | None = Field(
        default=None,
        description=(
            "Статус; у новой записи по умолчанию «открыто». Выполненное закрывай "
            f"memory_close_commitment. {KEEP_PREVIOUS}"
        ),
    )
    source: str | None = Field(
        default=None,
        description=f"Откуда факт: тема письма или «диалог». {KEEP_PREVIOUS}",
    )


class MemoryUpsertCommitmentTool(BaseTool):
    name: ClassVar[str] = "memory_upsert_commitment"
    description: ClassVar[str] = (
        "Добавляет или обновляет строку списка обязательств (что владелец обещал и чего ждёт "
        "от других). Строка ищется по паре «Что» + «Кто кому» без учёта регистра: "
        "совпала — обновляется, нет — добавляется. Вызывай, как только в разговоре "
        "прозвучало обещание или ожидание со сроком."
    )

    Input: ClassVar[type[BaseModel]] = MemoryUpsertCommitmentInput

    def __init__(self, commitments: ICommitmentStore) -> None:
        self._commitments = commitments

    def execute(self, input: MemoryUpsertCommitmentInput, context: ToolContext) -> str:
        try:
            existing = self._commitments.find(input.what, input.parties)
            commitment = Commitment.model_validate(
                {
                    **(existing.model_dump() if existing else {}),
                    **input.model_dump(exclude_none=True),
                }
            )
            outcome = self._commitments.upsert(commitment)
        except MEMORY_ERRORS as error:
            return error_reply(self._commitments.path, error)
        return success_reply(outcome.value, self._commitments.path, commitment)
