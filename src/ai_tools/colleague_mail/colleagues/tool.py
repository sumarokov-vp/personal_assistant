from typing import ClassVar

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel

from src.ai_tools.colleague_mail.colleagues.protocols.i_colleague import IColleague
from src.ai_tools.colleague_mail.colleagues.protocols.i_colleague_directory import (
    IColleagueDirectory,
)

NO_DIRECTORY = (
    "Справочник коллег не подключён (ASSISTANT_DIRECTORY_FILE не задан): ключи "
    "ассистентов коллег неизвестны."
)


class ColleaguesInput(BaseModel):
    pass


class ColleaguesTool(BaseTool):
    name: ClassVar[str] = "colleagues"
    description: ClassVar[str] = (
        "Справочник ассистентов коллег владельца: ключ (адрес для colleague_send), имя "
        "сотрудника и редактор ли он общих агентов."
    )
    Input: ClassVar[type[BaseModel]] = ColleaguesInput

    def __init__(self, directory: IColleagueDirectory | None) -> None:
        self._directory = directory

    def execute(self, input: ColleaguesInput, context: ToolContext) -> str:
        if self._directory is None:
            return NO_DIRECTORY
        colleagues = self._directory.colleagues()
        if not colleagues:
            return "Справочник коллег пуст."
        lines = "\n".join(self._line(colleague) for colleague in colleagues)
        return f"Коллеги в справочнике: {len(colleagues)}.\n{lines}"

    def _line(self, colleague: IColleague) -> str:
        role = " · редактор" if colleague.editor else ""
        return f"{colleague.key} · {colleague.name}{role}"
