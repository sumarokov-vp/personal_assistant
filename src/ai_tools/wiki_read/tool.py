import json
from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, Field

from src.ai_tools.wiki_read.protocols.i_wiki_page_reader import IWikiPageReader
from src.wiki.errors.wiki_error import WikiError

MAX_CONTENT_CHARS = 20_000


class WikiReadInput(BaseModel):
    path: str = Field(
        min_length=1,
        description=(
            "Путь страницы от корня вики, как его вернул wiki_search "
            "(например 'Wiki/Проекты/Ассистент.md')."
        ),
    )


class WikiReadTool(BaseTool):
    name: ClassVar[str] = "wiki_read"
    description: ClassVar[str] = (
        "Читает страницу вики владельца (Obsidian) целиком по пути от корня вики. "
        f"Страница длиннее {MAX_CONTENT_CHARS} знаков обрезается: truncated_chars "
        "показывает, сколько знаков срезано. Служебные каталоги (.obsidian, .git) "
        "недоступны. Путь не знаешь — сначала wiki_search. "
        "Отвечая по содержимому вики, всегда называй путь страницы, на которую опираешься."
    )

    Input: ClassVar[type[BaseModel]] = WikiReadInput

    def __init__(self, reader: IWikiPageReader) -> None:
        self._reader = reader

    def execute(self, input: WikiReadInput, context: ToolContext) -> str:  # noqa: A002
        try:
            page = self._reader.read_page(input.path)
        except WikiError as error:
            return json.dumps(
                {"status": "error", "path": input.path, "message": str(error)},
                ensure_ascii=False,
            )
        content = page.content[:MAX_CONTENT_CHARS]
        truncated_chars = len(page.content) - len(content)
        return json.dumps(
            {
                "status": "truncated" if truncated_chars else "ok",
                "path": page.path,
                "content": content,
                "truncated_chars": truncated_chars,
            },
            ensure_ascii=False,
        )
