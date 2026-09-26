import json
from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.checkup_skip.protocols.i_checkup_skipper import ICheckupSkipper
from src.checkup.services.checkup_actions.checkup_action_outcome import (
    CheckupActionOutcome,
)

_MESSAGES = {
    CheckupActionOutcome.SKIPPED: "записано в журнал чекапа без задачи",
    CheckupActionOutcome.ALREADY_DONE: "уже сделано: ключ есть в журнале чекапа, ничего не записано",
}


class CheckupSkipInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    key: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class CheckupSkipTool(BaseTool):
    name: ClassVar[str] = "checkup_skip"
    description: ClassVar[str] = (
        "Действие чекапа: у владельца уже есть своя задача на это — записывает в журнал "
        "чекапа, что задачу ставить не нужно, и ничего не создаёт в Todoist. "
        "key — запись реестра сроков в виде «Что | Чьё | ДД.ММ.ГГГГ» (дата — «Истекает»). "
        "reason — какая задача владельца это уже покрывает. "
        "Возвращает status (skipped | already_done), message и строку журнала."
    )

    Input: ClassVar[type[BaseModel]] = CheckupSkipInput

    def __init__(self, skipper: ICheckupSkipper) -> None:
        self._skipper = skipper

    def execute(self, input: CheckupSkipInput, context: ToolContext) -> str:
        result = self._skipper.skip(raw_key=input.key, reason=input.reason)
        return json.dumps(
            {
                "status": result.outcome.value,
                "message": _MESSAGES[result.outcome],
                "journal": result.journal_entry.model_dump(mode="json"),
            },
            ensure_ascii=False,
        )
