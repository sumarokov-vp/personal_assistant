import json
from datetime import date
from typing import ClassVar, Literal

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.task_add.task_assignee import ASSIGNEE_HINT, is_known_assignee
from src.ai_tools.task_update.protocols.i_task_changed_listener import (
    ITaskChangedListener,
)
from src.ai_tools.task_update.protocols.i_task_updater import ITaskUpdater
from src.cases.errors.cases_service_error import CasesServiceError
from src.cases.models.task_change import TaskChange


class TaskUpdateInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    task_id: str = Field(min_length=1)
    due: date | None = Field(default=None, description="Новый срок-дедлайн, YYYY-MM-DD")
    assignee: str | None = Field(
        default=None,
        description="Новый исполнитель: self, assistant, agent:<имя>, person:<имя>, "
        "colleague:<пользователь>",
    )
    summary: str = Field(
        min_length=1,
        description="Почему меняется: «нотариус перенёс приём на 15.10»",
    )
    source: Literal["owner", "assistant"] = Field(
        default="owner",
        description="owner — владелец попросил, assistant — ассистент решил сам",
    )


class TaskUpdateTool(BaseTool):
    name: ClassVar[str] = "task_update"
    description: ClassVar[str] = (
        "Меняет у задачи срок-дедлайн или исполнителя; в ленту дела ложится событие с "
        "причиной. Передавай только то, что меняешь. Закрыть задачу — task_close."
    )
    Input: ClassVar[type[BaseModel]] = TaskUpdateInput

    def __init__(
        self, updater: ITaskUpdater, listener: ITaskChangedListener | None = None
    ) -> None:
        self._updater = updater
        self._listener = listener

    def execute(self, input: TaskUpdateInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        if input.due is None and input.assignee is None:
            return _error("Нечего менять: передай due или assignee.")
        if input.assignee is not None and not is_known_assignee(input.assignee):
            return _error(
                f"Неизвестный исполнитель «{input.assignee}». {ASSIGNEE_HINT}"
            )
        change = TaskChange.model_validate(
            input.model_dump(
                include={"due", "assignee", "summary", "source"}, exclude_none=True
            )
        )
        try:
            task = self._updater.update_task(input.task_id, change)
        except CasesServiceError as error:
            return _error(str(error))
        if self._listener is not None:
            self._listener.task_changed(task)
        due = task.due.strftime("%d.%m.%Y") if task.due else "без срока"
        return (
            f"Задача обновлена: {task.id} · {task.status} · срок {due} · "
            f"исполнитель {task.assignee}"
        )


def _error(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)
