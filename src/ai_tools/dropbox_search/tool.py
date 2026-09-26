import json
from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, Field

from src.ai_tools.dropbox_search.protocols.i_dropbox_finder import IDropboxFinder
from src.dropbox.services.boundary.dropbox_access_denied_error import (
    DropboxAccessDeniedError,
)


class DropboxSearchInput(BaseModel):
    query: str
    within: str = ""
    limit: int = Field(default=30, ge=1, le=100)


class DropboxSearchTool(BaseTool):
    name: ClassVar[str] = "dropbox_search"
    description: ClassVar[str] = (
        "Ищет файлы и папки Dropbox по имени и пути (не по содержимому). "
        "query — слова через пробел, все должны встретиться в пути без учёта регистра "
        "(например «itinerary cnx» или «паспорт»). Имена файлов часто латиницей — "
        "если по-русски не нашлось, попробуй английские слова. "
        "within — искать только внутри папки (путь от корня Dropbox), пусто — везде. "
        "limit — сколько совпадений вернуть. Возвращает hits (path, is_folder, size, "
        "modified_at) и total — сколько совпало всего. Закрытые части Dropbox не ищутся."
    )

    Input: ClassVar[type[BaseModel]] = DropboxSearchInput

    def __init__(self, finder: IDropboxFinder) -> None:
        self._finder = finder

    def execute(self, input: DropboxSearchInput, context: ToolContext) -> str:  # noqa: A002
        try:
            result = self._finder.find(
                query=input.query, limit=input.limit, within=input.within
            )
        except (
            DropboxAccessDeniedError,
            FileNotFoundError,
            NotADirectoryError,
            ValueError,
        ) as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)
        return result.model_dump_json()
