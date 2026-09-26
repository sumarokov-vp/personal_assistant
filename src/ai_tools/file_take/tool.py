import json
from typing import ClassVar, Literal

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, Field

from src.ai_tools.file_take.file_take_refused_error import FileTakeRefusedError
from src.ai_tools.file_take.protocols.i_chat_file_source import IChatFileSource
from src.ai_tools.file_take.protocols.i_dropbox_file_source import (
    IDropboxFileSource,
)
from src.ai_tools.file_take.protocols.i_fetched_file import IFetchedFile
from src.ai_tools.file_take.protocols.i_mail_file_source import IMailFileSource
from src.ai_tools.file_take.protocols.i_work_file_writer import IWorkFileWriter
from src.dropbox.services.boundary.dropbox_access_denied_error import (
    DropboxAccessDeniedError,
)
from src.files.sources.entities.source_file_not_found_error import (
    SourceFileNotFoundError,
)
from src.files.sources.entities.source_file_too_large_error import (
    SourceFileTooLargeError,
)

FileSource = Literal["mail", "dropbox", "chat"]


class FileTakeInput(BaseModel):
    source: FileSource = Field(description="откуда взять файл: mail, dropbox или chat")
    message_id: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9]+$",
        description="source=mail: id письма из search_mail или read_mail",
    )
    attachment_id: str | None = Field(
        default=None,
        pattern=r"^[0-9.]+$",
        description="source=mail: attachment_id вложения из read_mail",
    )
    path: str | None = Field(
        default=None,
        description="source=dropbox: путь к файлу относительно корня Dropbox",
    )
    attachment_filename: str | None = Field(
        default=None,
        description=(
            "source=chat: имя вложения из метки «[вложение: …]» в сообщении "
            "владельца (photo_xxxxxxxx.jpg или исходное имя документа) или ключ "
            "S3; не указано — последнее присланное"
        ),
    )


class FileTakeTool(BaseTool):
    name: ClassVar[str] = "file_take"
    description: ClassVar[str] = (
        "Забирает файл в рабочую папку бота и возвращает file_id — с ним работают "
        "остальные файловые инструменты (file_read — прочитать текст). Источники: "
        "mail — вложение письма (message_id и attachment_id из read_mail); dropbox — "
        "файл по path относительно корня Dropbox; chat — вложение, которое владелец "
        "прислал в чат за всю историю треда: attachment_filename — имя из метки "
        "«[вложение: …]» его сообщения или ключ S3, не указано — последнее. Отвечает {file_id, name, media_type, size}. Файл живёт в рабочей "
        "папке сутки. Больше 50 МБ, ключевые файлы и закрытые части Dropbox — error."
    )

    Input: ClassVar[type[BaseModel]] = FileTakeInput

    def __init__(
        self,
        work_files: IWorkFileWriter,
        chat: IChatFileSource,
        dropbox: IDropboxFileSource | None,
        mail: IMailFileSource | None,
    ) -> None:
        self._work_files = work_files
        self._chat = chat
        self._dropbox = dropbox
        self._mail = mail

    def execute(self, input: FileTakeInput, context: ToolContext) -> str:  # noqa: A002
        try:
            fetched, source = self._fetch(input, str(context.user_id))
        except KeyError:
            return _error(
                "Вложения больше нет в хранилище — попроси прислать файл заново"
            )
        except (
            FileTakeRefusedError,
            SourceFileNotFoundError,
            SourceFileTooLargeError,
            DropboxAccessDeniedError,
            FileNotFoundError,
            IsADirectoryError,
        ) as error:
            return _error(str(error))
        work_file = self._work_files.put(
            fetched.content, fetched.name, fetched.media_type, source
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

    def _fetch(
        self,
        input: FileTakeInput,
        thread_id: str,  # noqa: A002
    ) -> tuple[IFetchedFile, str]:
        if input.source == "mail":
            return self._fetch_mail(input)
        if input.source == "dropbox":
            return self._fetch_dropbox(input)
        return (
            self._chat.fetch(thread_id, input.attachment_filename),
            "chat",
        )

    def _fetch_mail(self, input: FileTakeInput) -> tuple[IFetchedFile, str]:  # noqa: A002
        if self._mail is None:
            raise FileTakeRefusedError(
                "Почта не подключена — вложения писем не достать"
            )
        if not input.message_id or not input.attachment_id:
            raise FileTakeRefusedError(
                "Для source=mail нужны message_id и attachment_id из read_mail"
            )
        return (
            self._mail.fetch(input.message_id, input.attachment_id),
            f"mail:{input.message_id}/{input.attachment_id}",
        )

    def _fetch_dropbox(self, input: FileTakeInput) -> tuple[IFetchedFile, str]:  # noqa: A002
        if self._dropbox is None:
            raise FileTakeRefusedError(
                "Dropbox не подключён — файлы из него не достать"
            )
        if not input.path or not input.path.strip():
            raise FileTakeRefusedError("Для source=dropbox нужен path")
        return self._dropbox.fetch(input.path), f"dropbox:{input.path.strip()}"


def _error(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)
