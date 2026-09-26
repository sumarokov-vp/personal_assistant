import json
from datetime import date
from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.create_task.protocols.i_assistant_task_creator import (
    IAssistantTaskCreator,
)
from src.todoist.services.todoist_task_service.todoist_project_not_found_error import (
    TodoistProjectNotFoundError,
)


class CreateTaskInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(min_length=1)
    due: str | None = None
    deadline: date | None = None
    description: str | None = None
    parent_id: str | None = None
    project: str | None = None
    create_project: bool = False
    labels: list[str] = Field(default_factory=list)


class CreateTaskTool(BaseTool):
    name: ClassVar[str] = "create_task"
    description: ClassVar[str] = (
        "Заводит задачу (дело) или подзадачу в Todoist владельца. Метку pa код ставит сам — "
        "так видно, что задача в ведении ассистента. "
        "content — формулировка задачи, коротко и с глаголом. "
        "due — срок: когда владелец планирует заняться. Необязателен: не назван и из "
        "разговора не следует — не передавай. Дата «2026-10-01», дата и время "
        "«2026-10-01 10:00» или фраза Todoist («завтра», «в пятницу в 15:00», "
        "«каждый понедельник»). "
        "deadline — дедлайн: жёсткая внешняя граница, только дата YYYY-MM-DD "
        "(истекает справка, крайний срок подачи). Срок и дедлайн — разные поля, одно "
        "в другое не подставляй. "
        "description — подробности, необязательно. "
        "parent_id — id задачи-родителя: так расписываются подзадачи дела. "
        "project — имя существующего проекта, только если владелец его назвал; без него "
        "задача идёт во «Входящие». Проекта с таким именем нет — вернётся error. "
        "create_project — true, только если владелец прямо велел завести новый проект. "
        "labels — тематические метки, только названные владельцем; свои не придумывай. "
        "Закрыть или удалить задачу этот инструмент не может. "
        "Возвращает созданную задачу: id, content, description, due, deadline, parent_id, "
        "labels, project, url."
    )

    Input: ClassVar[type[BaseModel]] = CreateTaskInput

    def __init__(self, creator: IAssistantTaskCreator) -> None:
        self._creator = creator

    def execute(self, input: CreateTaskInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        try:
            card = self._creator.create_assistant_task(
                content=input.content,
                due=input.due or None,
                description=input.description or None,
                deadline=input.deadline.isoformat() if input.deadline else None,
                parent_id=input.parent_id or None,
                project=input.project or None,
                labels=[label for label in input.labels if label],
                create_project=input.create_project,
            )
        except TodoistProjectNotFoundError as error:
            return json.dumps(
                {
                    "error": f"{error}. Задача не создана. Новый проект — только "
                    "create_project=true по прямому указанию владельца."
                },
                ensure_ascii=False,
            )
        return card.model_dump_json()
