import json
from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, Field

from src.ai_tools.wiki_search.protocols.i_wiki_searcher import IWikiSearcher
from src.wiki.errors.wiki_error import WikiError

DEFAULT_LIMIT = 10
MAX_LIMIT = 30


class WikiSearchInput(BaseModel):
    query: str = Field(
        min_length=1,
        description=(
            "Что искать: слово, фраза или часть имени страницы. "
            "Регистр не важен; несколько слов — страница должна содержать все."
        ),
    )
    limit: int = Field(
        default=DEFAULT_LIMIT,
        ge=1,
        le=MAX_LIMIT,
        description="Сколько страниц вернуть, лучшие первыми.",
    )


class WikiSearchTool(BaseTool):
    name: ClassVar[str] = "wiki_search"
    description: ClassVar[str] = (
        "Полнотекстовый поиск по вики владельца (Obsidian). Возвращает страницы: "
        "path — путь от корня вики, title — заголовок, snippet — строки вокруг "
        "совпадения. Совпадение в имени страницы стоит выше совпадения в тексте. "
        "Чтобы прочитать страницу целиком — wiki_read с этим path. "
        "Отвечая по содержимому вики, всегда называй путь страницы, на которую опираешься."
    )

    Input: ClassVar[type[BaseModel]] = WikiSearchInput

    def __init__(self, searcher: IWikiSearcher) -> None:
        self._searcher = searcher

    def execute(self, input: WikiSearchInput, context: ToolContext) -> str:  # noqa: A002
        try:
            hits = self._searcher.search(input.query, input.limit)
        except WikiError as error:
            return json.dumps(
                {"status": "error", "message": str(error)}, ensure_ascii=False
            )
        return json.dumps(
            {
                "status": "found" if hits else "not_found",
                "query": input.query,
                "results": [
                    {"path": hit.path, "title": hit.title, "snippet": hit.snippet}
                    for hit in hits
                ],
            },
            ensure_ascii=False,
        )
