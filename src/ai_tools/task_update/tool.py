import json
from datetime import date
from typing import ClassVar, Literal

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.task_add.task_assignee import ASSIGNEE_HINT, is_known_assignee
from src.ai_tools.task_update.protocols.i_task_changed_listener import (
    ITaskChangedListener,
)
from src.ai_tools.task_update.protocols.i_task_planner import ITaskPlanner
from src.ai_tools.task_update.protocols.i_task_updater import ITaskUpdater
from src.cases.errors.cases_service_error import CasesServiceError
from src.cases.models.case_task import CaseTask
from src.cases.models.task_change import TaskChange
from src.task_manager.errors.task_manager_error import TaskManagerError

NO_TASK_MANAGER = (
    "Задачник владельца не подключён: дату выполнения ставить некуда. "
    "Срок-дедлайн меняет due."
)


class TaskUpdateInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    task_id: str = Field(min_length=1)
    planned: date | None = Field(
        default=None,
        description="Новая дата выполнения — когда владелец займётся задачей, "
        "YYYY-MM-DD. Это «перенеси на пятницу»; уходит в задачник владельца, "
        "в ленту кейса — событие с причиной",
    )
    due: date | None = Field(
        default=None,
        description="Новый срок-дедлайн, YYYY-MM-DD — только когда владелец прямо "
        "говорит о дедлайне",
    )
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
        "Меняет у задачи дату выполнения (planned — перенос «на пятницу», уходит в "
        "задачник владельца), срок-дедлайн (due) или исполнителя; в ленту кейса ложится "
        "событие с причиной. Передавай только то, что меняешь. Повторяющуюся задачу "
        "не переносит. Закрыть задачу — task_close."
    )
    Input: ClassVar[type[BaseModel]] = TaskUpdateInput

    def __init__(
        self,
        updater: ITaskUpdater,
        listener: ITaskChangedListener | None = None,
        planner: ITaskPlanner | None = None,
    ) -> None:
        self._updater = updater
        self._listener = listener
        self._planner = planner

    def execute(self, input: TaskUpdateInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        if input.planned is None and input.due is None and input.assignee is None:
            return _error("Нечего менять: передай planned, due или assignee.")
        if input.assignee is not None and not is_known_assignee(input.assignee):
            return _error(
                f"Неизвестный исполнитель «{input.assignee}». {ASSIGNEE_HINT}"
            )
        if input.planned is not None and self._planner is None:
            return _error(NO_TASK_MANAGER)
        fields_changed = input.due is not None or input.assignee is not None
        change = TaskChange.model_validate(
            input.model_dump(
                include={"due", "assignee", "summary", "source"}, exclude_none=True
            )
        )
        try:
            task = self._updater.update_task(input.task_id, change)
        except CasesServiceError as error:
            return _error(str(error))
        if fields_changed and self._listener is not None:
            self._listener.task_changed(task)
        answer = _task_line(task) if fields_changed else ""
        if input.planned is None or self._planner is None:
            return answer
        try:
            self._planner.reschedule(task, input.planned, input.summary, input.source)
        except (TaskManagerError, CasesServiceError) as error:
            refusal = f"Дата выполнения не перенесена: {error}"
            return _error(f"{answer}\n{refusal}" if answer else refusal)
        moved = f"Дата выполнения {input.planned.strftime('%d.%m.%Y')}: {task.id}"
        return f"{answer}\n{moved}" if answer else moved


def _task_line(task: CaseTask) -> str:
    due = task.due.strftime("%d.%m.%Y") if task.due else "без срока"
    return (
        f"Задача обновлена: {task.id} · {task.status} · срок {due} · "
        f"исполнитель {task.assignee}"
    )


def _error(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)
