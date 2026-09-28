import json
from collections.abc import Sequence
from typing import Any, ClassVar

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, Field

from src.ai_tools.file_take.file_take_refused_error import FileTakeRefusedError
from src.ai_tools.file_take.protocols.i_fetched_file import IFetchedFile
from src.ai_tools.file_take.protocols.i_work_file_writer import IWorkFileWriter
from src.ai_tools.file_take.registered_file_source import RegisteredFileSource
from src.conversations.errors.conversation_source_error import (
    ConversationSourceError,
)
from src.files.sources.entities.file_request import FileRequest
from src.files.sources.entities.file_request_incomplete_error import (
    FileRequestIncompleteError,
)
from src.files.sources.entities.file_source_unavailable_error import (
    FileSourceUnavailableError,
)
from src.files.sources.entities.source_file_not_found_error import (
    SourceFileNotFoundError,
)
from src.files.sources.entities.source_file_too_large_error import (
    SourceFileTooLargeError,
)

SOURCE_KEY_PATTERN = r"^[a-z][a-z0-9_]*$"
SOURCE_ITEM_ID_PATTERN = r"^[A-Za-z0-9._:@-]+$"


class FileTakeInput(BaseModel):
    source: str = Field(pattern=SOURCE_KEY_PATTERN, description="откуда взять файл")
    message_id: str | None = Field(
        default=None,
        pattern=SOURCE_ITEM_ID_PATTERN,
        description="id сообщения, к которому приложен файл (письмо, сообщение переписки)",
    )
    attachment_id: str | None = Field(
        default=None,
        pattern=SOURCE_ITEM_ID_PATTERN,
        description="attachment_id вложения этого сообщения",
    )
    path: str | None = Field(
        default=None,
        description="путь к файлу в хранилище источника",
    )
    attachment_filename: str | None = Field(
        default=None,
        description=(
            "имя вложения из метки «[вложение: …]» в сообщении владельца "
            "(photo_xxxxxxxx.jpg или исходное имя документа) или ключ S3; "
            "не указано — последнее присланное"
        ),
    )


class FileTakeTool(BaseTool):
    name: ClassVar[str] = "file_take"
    description: ClassVar[str] = (
        "Забирает файл в рабочую папку бота и возвращает file_id — с ним работают "
        "остальные файловые инструменты (file_read — прочитать текст). Источник — "
        "source; какие поля нужны каждому источнику, сказано в описании source. "
        "Отвечает {file_id, name, media_type, size}. Файл живёт в рабочей папке "
        "сутки. Больше 50 МБ, ключевые файлы и закрытые части Dropbox — error."
    )

    Input: ClassVar[type[BaseModel]] = FileTakeInput

    def __init__(
        self, work_files: IWorkFileWriter, sources: Sequence[RegisteredFileSource]
    ) -> None:
        self._work_files = work_files
        self._sources = {registered.key: registered for registered in sources}

    @property
    def input_schema(self) -> dict[str, Any]:
        schema = super().input_schema
        source = schema["properties"]["source"]
        source["enum"] = list(self._sources)
        source["description"] = "откуда взять файл: " + "; ".join(
            f"{registered.key} — {registered.hint}"
            for registered in self._sources.values()
        )
        return schema

    def execute(self, input: FileTakeInput, context: ToolContext) -> str:  # noqa: A002
        try:
            fetched = self._fetch(input, str(context.user_id))
        except KeyError:
            return _error(
                "Вложения больше нет в хранилище — попроси прислать файл заново"
            )
        except (
            FileTakeRefusedError,
            FileSourceUnavailableError,
            FileRequestIncompleteError,
            SourceFileNotFoundError,
            SourceFileTooLargeError,
            ConversationSourceError,
            PermissionError,
            FileNotFoundError,
            IsADirectoryError,
        ) as error:
            return _error(str(error))
        work_file = self._work_files.put(
            fetched.content, fetched.name, fetched.media_type, fetched.origin
        )
        return json.dumps(
            {
                "file_id": work_file.id,
                "name": work_file.name,
                "media_type": work_file.media_type,
                "size": work_file.size,
            },
            ensure_ascii=False,
        )

    def _fetch(self, input: FileTakeInput, thread_id: str) -> IFetchedFile:  # noqa: A002
        registered = self._sources.get(input.source)
        if registered is None:
            raise FileTakeRefusedError(
                f"Источника «{input.source}» нет. Есть: {', '.join(self._sources)}"
            )
        return registered.source.fetch(
            FileRequest(
                thread_id=thread_id,
                message_id=input.message_id,
                attachment_id=input.attachment_id,
                path=input.path,
                name=input.attachment_filename,
            )
        )


def _error(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)
