from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.add_task_link.protocols.i_task_link_adder import ITaskLinkAdder


class AddTaskLinkInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    task_id: str = Field(min_length=1)
    link: str = Field(min_length=1)
    note: str | None = None


class AddTaskLinkTool(BaseTool):
    name: ClassVar[str] = "add_task_link"
    description: ClassVar[str] = (
        "Дописывает к задаче (делу) Todoist одну ссылку — отдельным комментарием. "
        "Одна ссылка — один вызов. task_id — id задачи. "
        "link — сама ссылка: путь страницы вики, путь файла или папки Dropbox, id треда "
        "или поисковый запрос Gmail, чат или сообщение WhatsApp, контакт. "
        "note — коротко, что по ссылке и зачем она делу, необязательно. "
        "Возвращает созданный комментарий: id, content, posted_at."
    )

    Input: ClassVar[type[BaseModel]] = AddTaskLinkInput

    def __init__(self, adder: ITaskLinkAdder) -> None:
        self._adder = adder

    def execute(self, input: AddTaskLinkInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        content = f"{input.link} — {input.note}" if input.note else input.link
        return self._adder.add_link(
            task_id=input.task_id, link=content
        ).model_dump_json()
