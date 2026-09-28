import json
from typing import ClassVar

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.task_link_todoist.protocols.i_todoist_task_adopter import (
    ITodoistTaskAdopter,
)
from src.cases.errors.cases_service_error import CasesServiceError
from src.todoist.repos.todoist_error import TodoistError

INBOX_CASE_ID = "inbox"


class TaskLinkTodoistInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    todoist_task_id: str = Field(
        min_length=1, description="id задачи Todoist из find_tasks или read_task"
    )
    case_id: str | None = Field(
        default=None,
        description="Дело, к которому подвязать задачу. Не относится ни к какому — не "
        "передавай: задача ляжет в служебное дело «Без темы»",
    )
    summary: str | None = Field(
        default=None,
        min_length=1,
        description="Что сделать и зачем; не передано — текст задачи Todoist",
    )


class TaskLinkTodoistTool(BaseTool):
    name: ClassVar[str] = "task_link_todoist"
    description: ClassVar[str] = (
        "Подвязывает к делу задачу, которую владелец сам завёл в Todoist: она "
        "становится нашей задачей с исполнителем self, и дальше её закрытие, "
        "удаление и смену дедлайна в Todoist ассистент переносит в ленту дела. "
        "Только когда владелец поднял эту тему; уже подвязанная задача второй раз "
        "не записывается."
    )
    Input: ClassVar[type[BaseModel]] = TaskLinkTodoistInput

    def __init__(self, adopter: ITodoistTaskAdopter) -> None:
        self._adopter = adopter

    def execute(self, input: TaskLinkTodoistInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        try:
            task = self._adopter.adopt(
                todoist_task_id=input.todoist_task_id,
                case_id=input.case_id or INBOX_CASE_ID,
                summary=input.summary,
            )
        except (CasesServiceError, TodoistError, LookupError) as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)
        due = task.due.strftime("%d.%m.%Y") if task.due else "без срока"
        return (
            f"Задача Todoist подвязана: {task.id} · дело «{task.case.title}» · "
            f"{task.status} · срок {due}"
        )
