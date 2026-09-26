from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.read_task.protocols.i_task_reader import ITaskReader


class ReadTaskInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    task_id: str = Field(min_length=1)


class ReadTaskTool(BaseTool):
    name: ClassVar[str] = "read_task"
    description: ClassVar[str] = (
        "Читает задачу (дело) Todoist целиком. task_id — id из find_tasks или create_task. "
        "Возвращает task (id, content, description, due, deadline, parent_id, labels, "
        "project, url), subtasks — подзадачи в том же виде, comments (id, content, "
        "posted_at) — ссылки дела: страницы вики, файлы Dropbox, письма и запросы Gmail, "
        "контакты. Отвечая по делу, иди по этим ссылкам."
    )

    Input: ClassVar[type[BaseModel]] = ReadTaskInput

    def __init__(self, reader: ITaskReader) -> None:
        self._reader = reader

    def execute(self, input: ReadTaskInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        return self._reader.read_task(input.task_id).model_dump_json()
