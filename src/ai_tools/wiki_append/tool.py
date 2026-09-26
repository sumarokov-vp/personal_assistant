import json
from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.wiki_append.protocols.i_wiki_page_appender import IWikiPageAppender
from src.wiki import WikiError

PAGE_SUFFIX = ".md"
BLOCK_SEPARATOR = "\n"


class WikiAppendInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    path: str = Field(min_length=1)
    content: str = Field(min_length=1)


class WikiAppendTool(BaseTool):
    name: ClassVar[str] = "wiki_append"
    description: ClassVar[str] = (
        "Дописывает блок в конец существующей страницы вики Obsidian владельца, "
        "отделяя его пустой строкой; сразу коммит и push в main. "
        "path — путь страницы от корня вики, как его вернули wiki_search, "
        "wiki_read или wiki_create_page (например Wiki/Проект.md). "
        "content — дописываемый markdown. "
        "Страницы нет — вернётся error; новую страницу создаёт wiki_create_page. "
        "В дневник (Daily/YYYY-MM-DD.md) писать только если владелец прямо сказал "
        "«в дневник»; надиктованная заметка без такой просьбы — новая страница "
        "через wiki_create_page. "
        "Возвращает path дополненной страницы — назови его владельцу."
    )

    Input: ClassVar[type[BaseModel]] = WikiAppendInput

    def __init__(self, appender: IWikiPageAppender) -> None:
        self._appender = appender

    def execute(self, input: WikiAppendInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        relative_path = _with_page_suffix(input.path.strip("/"))
        try:
            result = self._appender.append_to_page(
                relative_path,
                BLOCK_SEPARATOR + input.content,
                f"дополнена {relative_path}",
            )
        except WikiError as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)
        return json.dumps({"path": result.path}, ensure_ascii=False)


def _with_page_suffix(path: str) -> str:
    return path if path.endswith(PAGE_SUFFIX) else path + PAGE_SUFFIX
