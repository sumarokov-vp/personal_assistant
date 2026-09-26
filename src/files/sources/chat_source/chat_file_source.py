from ai_framework import Attachment

from src.files.sources.chat_source.chat_file_name import chat_file_name
from src.files.sources.chat_source.protocols.i_chat_attachments import (
    IChatAttachments,
)
from src.files.sources.entities.fetched_file import FetchedFile
from src.files.sources.entities.source_file_not_found_error import (
    SourceFileNotFoundError,
)
from src.files.sources.entities.source_file_too_large_error import (
    SourceFileTooLargeError,
)


class ChatFileSource:
    def __init__(self, attachments: IChatAttachments, max_bytes: int) -> None:
        self._attachments = attachments
        self._max_bytes = max_bytes

    def fetch(self, thread_id: str, filename: str | None) -> FetchedFile:
        recent = self._attachments.recent(thread_id)
        attachment = _pick(recent, filename)
        name = chat_file_name(attachment)
        content = self._attachments.content(attachment)
        if len(content) > self._max_bytes:
            raise SourceFileTooLargeError(name, self._max_bytes)
        return FetchedFile(content=content, name=name, media_type=attachment.media_type)


def _pick(recent: list[Attachment], filename: str | None) -> Attachment:
    if not recent:
        raise SourceFileNotFoundError(
            "В недавних сообщениях нет вложений — попроси прислать файл в чат"
        )
    if not filename:
        return recent[0]
    wanted = filename.strip().casefold()
    found = next(
        (item for item in recent if (item.filename or "").casefold() == wanted), None
    )
    if found is None:
        names = ", ".join(item.filename or "фото без имени" for item in recent)
        raise SourceFileNotFoundError(
            f"Вложения «{filename}» нет среди недавних: {names}"
        )
    return found
