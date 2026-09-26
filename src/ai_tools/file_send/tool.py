import json
from typing import ClassVar

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, Field

from src.ai_tools.file_send.protocols.i_document_sender import IDocumentSender
from src.ai_tools.file_send.protocols.i_overflow_folder import IOverflowFolder
from src.ai_tools.file_send.protocols.i_work_file_reader import IWorkFileReader
from src.files.work_folder.work_file_not_found_error import WorkFileNotFoundError

OVERFLOW_NOTE = (
    "Файл больше предела Telegram-бота на отправку и не прислан в чат: он лежит в "
    "Dropbox по пути path. Папка временная — через сутки файл удалится сам; чтобы "
    "сохранить надолго, его надо переложить в постоянную папку"
)


class FileSendInput(BaseModel):
    file_id: str = Field(description="file_id из ответа file_take")


class FileSendTool(BaseTool):
    name: ClassVar[str] = "file_send"
    description: ClassVar[str] = (
        "Присылает владельцу в его чат с ботом файл из рабочей папки по file_id (его "
        "возвращает file_take) — документом, как есть. Отправляет только владельцу: "
        "другого адресата нет. Файл больше 50 МБ Telegram-бот отправить не может — он "
        "кладётся в папку «Personal Assistant» в Dropbox, и ответ возвращает path; его "
        "назови владельцу. Неизвестный file_id — error."
    )

    Input: ClassVar[type[BaseModel]] = FileSendInput

    def __init__(
        self,
        work_files: IWorkFileReader,
        sender: IDocumentSender,
        owner_chat_id: int,
        size_limit_bytes: int,
        overflow: IOverflowFolder | None,
    ) -> None:
        self._work_files = work_files
        self._sender = sender
        self._owner_chat_id = owner_chat_id
        self._size_limit_bytes = size_limit_bytes
        self._overflow = overflow

    def execute(self, input: FileSendInput, context: ToolContext) -> str:  # noqa: A002
        try:
            return self._deliver(input.file_id.strip())
        except WorkFileNotFoundError as error:
            return _error(str(error))

    def _deliver(self, file_id: str) -> str:
        work_file = self._work_files.get(file_id)
        if work_file.size <= self._size_limit_bytes:
            self._sender.send_document(
                chat_id=self._owner_chat_id,
                document=self._work_files.read(file_id),
                filename=work_file.name,
            )
            return json.dumps(
                {"sent": True, "name": work_file.name}, ensure_ascii=False
            )
        if self._overflow is None:
            return _error(
                f"Файл «{work_file.name}» больше 50 МБ: Telegram-бот его не "
                "отправит, а Dropbox боту не подключён — положить некуда"
            )
        return json.dumps(
            {
                "sent": False,
                "path": self._overflow.place(work_file),
                "note": OVERFLOW_NOTE,
            },
            ensure_ascii=False,
        )


def _error(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)
