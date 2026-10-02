import json
from datetime import date
from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.find_tasks.protocols.i_task_finder import ITaskFinder
from src.task_manager.errors.task_manager_error import TaskManagerError
from src.task_manager.models.task_search import TaskSearch


class FindTasksInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str | None = Field(
        default=None,
        min_length=1,
        description="Слова из текста задачи; не передано — без поиска по тексту",
    )
    due_before: date | None = Field(
        default=None,
        description="Только задачи с датой выполнения раньше этого дня (YYYY-MM-DD)",
    )
    overdue: bool = Field(default=False, description="Только просроченные")
    by_assistant: bool = Field(
        default=False, description="Только задачи, которые поставил ассистент"
    )
    limit: int = Field(default=50, ge=1, le=200)


class FindTasksTool(BaseTool):
    name: ClassVar[str] = "find_tasks"
    description: ClassVar[str] = (
        "Ищет активные задачи в задачнике пользователя; только чтение — задачу этот "
        "инструмент не заводит, не меняет и не закрывает. Условия складываются через «и»: "
        "text — слова из текста задачи, due_before — дата выполнения раньше дня, "
        "overdue — только просроченные, by_assistant — только поставленные ассистентом; "
        "без условий — все активные задачи. limit — сколько задач вернуть максимум. "
        "Возвращает tasks (ref, title, description, due — дата выполнения, deadline, "
        "recurring, by_assistant, labels, project, parent_ref, url) и count. "
        "ref — адрес задачи для read_task; url — ссылка на задачу, её можно дать "
        "пользователю. Сбой задачника вернёт error."
    )

    Input: ClassVar[type[BaseModel]] = FindTasksInput

    def __init__(self, finder: ITaskFinder) -> None:
        self._finder = finder

    def execute(self, input: FindTasksInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        search = TaskSearch(
            text=input.text,
            due_before=input.due_before,
            overdue=input.overdue,
            by_assistant=input.by_assistant,
            limit=input.limit,
        )
        try:
            tasks = self._finder.find_tasks(search)
        except TaskManagerError as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)
        return json.dumps(
            {
                "tasks": [task.model_dump(mode="json") for task in tasks],
                "count": len(tasks),
            },
            ensure_ascii=False,
        )
