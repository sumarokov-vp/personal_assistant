import json
from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel

from src.ai_tools.dropbox_read.protocols.i_dropbox_file_reader import (
    IDropboxFileReader,
)
from src.dropbox.services.boundary.dropbox_access_denied_error import (
    DropboxAccessDeniedError,
)
from src.files.readers.unreadable_format_error import UnreadableFormatError


class DropboxReadInput(BaseModel):
    path: str


class DropboxReadTool(BaseTool):
    name: ClassVar[str] = "dropbox_read"
    description: ClassVar[str] = (
        "Читает текст файла Dropbox пользователя; только чтение. "
        "path — путь к файлу относительно корня Dropbox, "
        "как его вернули dropbox_search или dropbox_tree. Читаются txt, md, csv, json, "
        "текстовый слой PDF, DOCX (абзацы, затем таблицы строками через таб) и XLSX "
        "(каждый лист — «## <имя листа>», строки через таб); .doc, .xls, картинки, "
        "сканы и прочие форматы вернут error. "
        "Длинный текст обрезается — тогда truncated=true. "
        "Ключевые файлы (.p12, .pfx, .key, .pem, .jks, .gpg) и закрытые части Dropbox "
        "не читаются — вернётся error."
    )

    Input: ClassVar[type[BaseModel]] = DropboxReadInput

    def __init__(self, reader: IDropboxFileReader) -> None:
        self._reader = reader

    def execute(self, input: DropboxReadInput, context: ToolContext) -> str:  # noqa: A002
        try:
            file_text = self._reader.read(input.path)
        except (
            DropboxAccessDeniedError,
            UnreadableFormatError,
            FileNotFoundError,
            IsADirectoryError,
        ) as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)
        return file_text.model_dump_json()
