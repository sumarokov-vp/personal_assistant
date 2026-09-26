import json
from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.checkup_create_task.checkup_run_missing_error import (
    CheckupRunMissingError,
)
from src.ai_tools.checkup_create_task.protocols.i_checkup_task_creator import (
    ICheckupTaskCreator,
)
from src.checkup.services.checkup_actions.checkup_action_outcome import (
    CheckupActionOutcome,
)
from src.checkup.services.entities.checkup_run import (
    CHECKUP_RUN_CONTEXT_KEY,
    CheckupRun,
)

_MESSAGES = {
    CheckupActionOutcome.CREATED: "задача создана и записана в журнал чекапа",
    CheckupActionOutcome.ALREADY_DONE: "уже сделано: ключ есть в журнале чекапа, задача не создана",
}


class CheckupCreateTaskInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    key: str = Field(min_length=1)
    content: str = Field(min_length=1)
    due: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class CheckupCreateTaskTool(BaseTool):
    name: ClassVar[str] = "checkup_create_task"
    description: ClassVar[str] = (
        "Действие чекапа: ставит владельцу задачу в Todoist (метка pa) и записывает её "
        "в журнал чекапа, чтобы следующий прогон её не повторил. "
        "key — запись реестра сроков в виде «Что | Чьё | ДД.ММ.ГГГГ» (дата — «Истекает»); "
        "если такой ключ уже в журнале, задача не создаётся и ответ — already_done. "
        "content — формулировка задачи, коротко и с глаголом. "
        "due — срок задачи: дата «2026-11-05» или фраза Todoist. "
        "reason — почему задача нужна сейчас, одной фразой: её прочитает владелец. "
        "Возвращает status (created | already_done), message и строку журнала."
    )

    Input: ClassVar[type[BaseModel]] = CheckupCreateTaskInput

    def __init__(self, creator: ICheckupTaskCreator) -> None:
        self._creator = creator

    def execute(self, input: CheckupCreateTaskInput, context: ToolContext) -> str:
        run = context.get(CHECKUP_RUN_CONTEXT_KEY)
        if not isinstance(run, CheckupRun):
            raise CheckupRunMissingError()
        result = self._creator.create_task(
            raw_key=input.key,
            content=input.content,
            due=input.due,
            reason=input.reason,
            run=run,
        )
        return json.dumps(
            {
                "status": result.outcome.value,
                "message": _MESSAGES[result.outcome],
                "journal": result.journal_entry.model_dump(mode="json"),
            },
            ensure_ascii=False,
        )
