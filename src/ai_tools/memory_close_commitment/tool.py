import json
from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, Field

from src.ai_tools.memory_close_commitment.protocols.i_commitment_closer import (
    ICommitmentCloser,
)
from src.ai_tools.memory_common import MEMORY_ERRORS, error_reply, success_reply

NOT_FOUND_MESSAGE = (
    "Такого обязательства нет. Посмотри memory_show и передай «Что» и «Кто кому» "
    "так, как они записаны в строке."
)


class MemoryCloseCommitmentInput(BaseModel):
    what: str = Field(
        description="«Что» существующего обязательства, как в memory_show."
    )
    parties: str = Field(
        description="«Кто кому» существующего обязательства, как в memory_show."
    )


class MemoryCloseCommitmentTool(BaseTool):
    name: ClassVar[str] = "memory_close_commitment"
    description: ClassVar[str] = (
        "Отмечает обязательство выполненным: статус становится «выполнено», строка "
        "остаётся на странице. Вызывай, когда владелец сообщил, что обещанное сделано "
        "или ожидаемое получено."
    )

    Input: ClassVar[type[BaseModel]] = MemoryCloseCommitmentInput

    def __init__(self, commitments: ICommitmentCloser) -> None:
        self._commitments = commitments

    def execute(self, input: MemoryCloseCommitmentInput, context: ToolContext) -> str:
        try:
            closed = self._commitments.close(input.what, input.parties)
        except MEMORY_ERRORS as error:
            return error_reply(self._commitments.path, error)
        if closed is None:
            return json.dumps(
                {
                    "status": "not_found",
                    "page": self._commitments.path,
                    "message": NOT_FOUND_MESSAGE,
                },
                ensure_ascii=False,
            )
        return success_reply("closed", self._commitments.path, closed)
