from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.create_task.protocols.i_assistant_task_creator import (
    IAssistantTaskCreator,
)


class CreateTaskInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(min_length=1)
    due: str = Field(min_length=1)
    description: str | None = None


class CreateTaskTool(BaseTool):
    name: ClassVar[str] = "create_task"
    description: ClassVar[str] = (
        "Создаёт задачу во Входящих Todoist владельца. Задача получает метку pa — "
        "так видно, что её поставил ассистент. "
        "content — формулировка задачи, коротко и с глаголом. "
        "due — срок, обязателен: дата «2026-10-01», дата и время «2026-10-01 10:00» "
        "или фраза Todoist («завтра», «в пятницу в 15:00», «каждый понедельник»). "
        "description — подробности, необязательно. "
        "Закрыть, изменить или удалить задачу этот инструмент не может. "
        "Возвращает созданную задачу: id, content, description, due, labels, project, url."
    )

    Input: ClassVar[type[BaseModel]] = CreateTaskInput

    def __init__(self, creator: IAssistantTaskCreator) -> None:
        self._creator = creator

    def execute(self, input: CreateTaskInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        card = self._creator.create_assistant_task(
            content=input.content,
            due=input.due,
            description=input.description or None,
        )
        return card.model_dump_json()
