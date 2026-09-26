import json
from collections.abc import Callable
from typing import ClassVar, Literal

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, Field

from src.ai_tools.memory_common import MEMORY_ERRORS, entry_view, error_view
from src.ai_tools.memory_show.protocols.i_memory_page_reader import IMemoryPageReader
from src.memory.models import Commitment, Deadline, Whereabouts

MemoryPageName = Literal["deadlines", "whereabouts", "commitments"]


class MemoryShowInput(BaseModel):
    page: MemoryPageName | Literal["all"] = Field(
        default="all",
        description=(
            "Какую страницу памяти показать: deadlines — реестр сроков, "
            "whereabouts — где я буду, commitments — обязательства, all — все три."
        ),
    )


class MemoryShowTool(BaseTool):
    name: ClassVar[str] = "memory_show"
    description: ClassVar[str] = (
        "Показывает записи памяти ассистента из служебных страниц вики: реестр сроков "
        "(документы и всё истекающее), где владелец будет (поездки), обязательства. "
        "Вызывай, когда нужен факт из памяти или перед обновлением записи, чтобы "
        "взять точные «Что», «Чьё», «Кто кому» существующей строки. "
        "remarks — строки, которые не удалось разобрать: они сохранены на странице как есть."
    )

    Input: ClassVar[type[BaseModel]] = MemoryShowInput

    def __init__(
        self,
        deadlines: IMemoryPageReader[Deadline],
        whereabouts: IMemoryPageReader[Whereabouts],
        commitments: IMemoryPageReader[Commitment],
    ) -> None:
        self._pages: dict[MemoryPageName, Callable[[], dict[str, object]]] = {
            "deadlines": lambda: _page_view(deadlines),
            "whereabouts": lambda: _page_view(whereabouts),
            "commitments": lambda: _page_view(commitments),
        }

    def execute(self, input: MemoryShowInput, context: ToolContext) -> str:
        page = input.page
        names: list[MemoryPageName] = list(self._pages) if page == "all" else [page]
        return json.dumps(
            {"pages": [self._pages[name]() for name in names]}, ensure_ascii=False
        )


def _page_view[T: BaseModel](page: IMemoryPageReader[T]) -> dict[str, object]:
    try:
        read = page.read()
    except MEMORY_ERRORS as error:
        return dict(error_view(page.path, error))
    return {
        "page": page.path,
        "entries": [entry_view(entry) for entry in read.entries],
        "remarks": read.remarks,
    }
