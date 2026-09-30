import json
from typing import ClassVar

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.task_link.protocols.i_task_adopter import ITaskAdopter
from src.cases.errors.cases_service_error import CasesServiceError
from src.task_manager.errors.task_manager_error import TaskManagerError

INBOX_CASE_ID = "inbox"


class TaskLinkInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    task_ref: str = Field(
        min_length=1, description="ref задачи задачника из find_tasks или read_task"
    )
    case_id: str | None = Field(
        default=None,
        description="Кейс, к которому подвязать задачу. Не относится ни к какому — не "
        "передавай: задача ляжет в служебный кейс «Без темы»",
    )
    summary: str | None = Field(
        default=None,
        min_length=1,
        description="Что сделать и зачем; не передано — текст задачи из задачника",
    )


class TaskLinkTool(BaseTool):
    name: ClassVar[str] = "task_link"
    description: ClassVar[str] = (
        "Подвязывает к кейсу задачу, которую владелец сам завёл в своём задачнике: она "
        "становится нашей задачей с исполнителем self, дальше её переносят и закрывают "
        "инструменты задач кейса, а изменения из задачника попадают в ленту кейса. "
        "Только когда владелец поднял эту тему; уже подвязанная задача второй раз "
        "не записывается."
    )
    Input: ClassVar[type[BaseModel]] = TaskLinkInput

    def __init__(self, adopter: ITaskAdopter) -> None:
        self._adopter = adopter

    def execute(self, input: TaskLinkInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        try:
            task = self._adopter.adopt(
                task_ref=input.task_ref,
                case_id=input.case_id or INBOX_CASE_ID,
                summary=input.summary,
            )
        except (CasesServiceError, TaskManagerError, LookupError) as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)
        due = task.due.strftime("%d.%m.%Y") if task.due else "без срока"
        return (
            f"Задача подвязана: {task.id} · кейс «{task.case.title}» · "
            f"{task.status} · срок {due}"
        )
