import json
from pathlib import PurePosixPath
from typing import ClassVar

from ai_framework import Attachment
from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel

from src.ai_tools.dropbox_save.protocols.i_chat_attachments import IChatAttachments
from src.ai_tools.dropbox_save.protocols.i_dropbox_file_saver import (
    IDropboxFileSaver,
)
from src.ai_tools.dropbox_save.saved_file_name import saved_file_name
from src.dropbox.services.boundary.dropbox_access_denied_error import (
    DropboxAccessDeniedError,
)


class DropboxSaveInput(BaseModel):
    folder: str
    name: str | None = None
    attachment_filename: str | None = None


class DropboxSaveTool(BaseTool):
    name: ClassVar[str] = "dropbox_save"
    description: ClassVar[str] = (
        "Кладёт в Dropbox вложение (PDF или картинку), которое владелец прислал в чат — "
        "в этом или одном из недавних сообщений. folder — папка относительно корня "
        "Dropbox, как её показывает dropbox_tree; несуществующая папка будет создана. "
        "name — имя файла; не указано — исходное имя вложения, без расширения — "
        "расширение добавится само. attachment_filename — исходное имя нужного вложения "
        "(из строки «Файл …» сообщения); не указано — берётся последнее присланное. "
        "Существующий файл не перезаписывается: при совпадении имени добавляется « (2)». "
        "Возвращает path — итоговый путь; его и называй владельцу. Закрытые части "
        "Dropbox — error."
    )

    Input: ClassVar[type[BaseModel]] = DropboxSaveInput

    def __init__(self, attachments: IChatAttachments, saver: IDropboxFileSaver) -> None:
        self._attachments = attachments
        self._saver = saver

    def execute(self, input: DropboxSaveInput, context: ToolContext) -> str:  # noqa: A002
        recent = self._attachments.recent(str(context.user_id))
        attachment = _pick(recent, input.attachment_filename)
        if attachment is None:
            return _missing(recent, input.attachment_filename)
        name = saved_file_name(attachment, input.name)
        try:
            content = self._attachments.content(attachment)
        except KeyError:
            return _error(
                "Вложения больше нет в хранилище — попроси прислать файл заново"
            )
        try:
            path = self._saver.save(input.folder, name, content)
        except (DropboxAccessDeniedError, NotADirectoryError, FileExistsError) as error:
            return _error(str(error))
        return json.dumps(
            {
                "path": path,
                "renamed": PurePosixPath(path).name != name,
            },
            ensure_ascii=False,
        )


def _pick(recent: list[Attachment], filename: str | None) -> Attachment | None:
    if not filename:
        return recent[0] if recent else None
    wanted = filename.strip().casefold()
    return next(
        (
            attachment
            for attachment in recent
            if (attachment.filename or "").casefold() == wanted
        ),
        None,
    )


def _missing(recent: list[Attachment], filename: str | None) -> str:
    if not recent:
        return _error(
            "В недавних сообщениях нет вложений — попроси прислать файл в чат"
        )
    names = [attachment.filename or "фото без имени" for attachment in recent]
    return _error(f"Вложения «{filename}» нет среди недавних: {', '.join(names)}")


def _error(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)
