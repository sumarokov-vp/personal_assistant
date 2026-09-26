import json
import re
from pathlib import PurePosixPath
from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.wiki_create_page.protocols.i_wiki_page_creator import (
    IWikiPageCreator,
)
from src.ai_tools.wiki_create_page.protocols.i_wiki_page_lister import (
    IWikiPageLister,
)
from src.wiki import WikiError

FORBIDDEN_TITLE_CHARACTERS = re.compile(r'[/\\:*?"<>|]')
PAGE_SUFFIX = ".md"
DEFAULT_FOLDER = "Wiki"


class WikiCreatePageInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    folder: str = DEFAULT_FOLDER


class WikiCreatePageTool(BaseTool):
    name: ClassVar[str] = "wiki_create_page"
    description: ClassVar[str] = (
        "Создаёт новую страницу в вики Obsidian владельца: файл <folder>/<title>.md, "
        "сразу коммит и push в main — владелец получит её через синхронизацию. "
        "Надиктованная заметка — новая страница в папке Wiki (folder по умолчанию). "
        "В Daily/ (дневник, страница YYYY-MM-DD.md) писать только если владелец "
        "прямо сказал «в дневник»: сначала wiki_append в Daily/YYYY-MM-DD.md, "
        "а если такой страницы ещё нет — этот инструмент с folder=Daily и "
        "title=YYYY-MM-DD. "
        "title — название страницы, кириллица допустима; символы / \\ : * ? \" < > | "
        "из него убираются. content — markdown страницы, начинай с заголовка "
        "«# <title>». folder — только существующая папка вики (Wiki, Daily или "
        "вложенная, например Wiki/Проекты); новые папки не создаются. "
        "Страница уже есть — вернётся error, страница не перезаписывается: "
        "дописать в неё можно через wiki_append. "
        "Возвращает path созданной страницы — назови его владельцу."
    )

    Input: ClassVar[type[BaseModel]] = WikiCreatePageInput

    def __init__(self, creator: IWikiPageCreator, lister: IWikiPageLister) -> None:
        self._creator = creator
        self._lister = lister

    def execute(self, input: WikiCreatePageInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        file_name = _file_name(input.title)
        if not file_name:
            return _error(f"Из названия «{input.title}» не осталось допустимых символов")
        folder = input.folder.strip("/").strip()
        try:
            existing_folders = self._existing_folders()
            if folder not in existing_folders:
                return _error(
                    f"Папки «{folder}» нет в вики, новые папки не создаются. "
                    f"Папки верхнего уровня: {', '.join(_top_level(existing_folders))}"
                )
            relative_path = f"{folder}/{file_name}"
            result = self._creator.create_page(
                relative_path, input.content, f"создана {relative_path}"
            )
        except WikiError as error:
            return _error(str(error))
        return json.dumps({"path": result.path}, ensure_ascii=False)

    def _existing_folders(self) -> set[str]:
        return {
            parent.as_posix()
            for page in self._lister.read_all_pages()
            for parent in PurePosixPath(page.path).parents
            if parent.as_posix() != "."
        }


def _file_name(title: str) -> str:
    cleaned = " ".join(FORBIDDEN_TITLE_CHARACTERS.sub(" ", title).split())
    stem = cleaned.removesuffix(PAGE_SUFFIX).strip().lstrip(".").strip()
    return f"{stem}{PAGE_SUFFIX}" if stem else ""


def _top_level(folders: set[str]) -> list[str]:
    return sorted(folder for folder in folders if "/" not in folder)


def _error(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)
