import json
from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.read_task.protocols.i_task_reader import ITaskReader
from src.task_manager.errors.task_manager_error import TaskManagerError


class ReadTaskInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    task_ref: str = Field(min_length=1, description="ref задачи из find_tasks")


class ReadTaskTool(BaseTool):
    name: ClassVar[str] = "read_task"
    description: ClassVar[str] = (
        "Читает задачу задачника владельца целиком. task_ref — ref из find_tasks. "
        "Возвращает task (ref, title, description, due — дата выполнения, deadline, "
        "recurring, by_assistant, labels, project, parent_ref, url), subtasks — "
        "подзадачи в том же виде, comments (text, posted_at) — комментарии к задаче. "
        "Кейсы живут не в задачнике, а в ленте кейса."
    )

    Input: ClassVar[type[BaseModel]] = ReadTaskInput

    def __init__(self, reader: ITaskReader) -> None:
        self._reader = reader

    def execute(self, input: ReadTaskInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        try:
            details = self._reader.read_task(input.task_ref)
        except TaskManagerError as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)
        return details.model_dump_json()
