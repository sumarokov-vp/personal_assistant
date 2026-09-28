from ai_framework import Attachment

from src.files.sources.chat_source.chat_file_aliases import chat_file_aliases
from src.files.sources.chat_source.chat_file_name import chat_file_name
from src.files.sources.chat_source.protocols.i_chat_attachments import (
    IChatAttachments,
)
from src.files.sources.entities.fetched_file import FetchedFile
from src.files.sources.entities.file_request import FileRequest
from src.files.sources.entities.source_file_not_found_error import (
    SourceFileNotFoundError,
)
from src.files.sources.entities.source_file_too_large_error import (
    SourceFileTooLargeError,
)

LISTED_NAMES_LIMIT = 30
CHAT_ORIGIN = "chat"


class ChatFileSource:
    def __init__(self, attachments: IChatAttachments, max_bytes: int) -> None:
        self._attachments = attachments
        self._max_bytes = max_bytes

    def fetch(self, request: FileRequest) -> FetchedFile:
        newest_first = self._attachments.in_thread(request.thread_id)
        attachment = _pick(newest_first, request.name)
        name = chat_file_name(attachment)
        content = self._attachments.content(attachment)
        if len(content) > self._max_bytes:
            raise SourceFileTooLargeError(name, self._max_bytes)
        return FetchedFile(
            content=content,
            name=name,
            media_type=attachment.media_type,
            origin=CHAT_ORIGIN,
        )


def _pick(newest_first: list[Attachment], filename: str | None) -> Attachment:
    if not newest_first:
        raise SourceFileNotFoundError(
            "В истории чата нет вложений — попроси прислать файл в чат"
        )
    if not filename:
        return newest_first[0]
    wanted = filename.strip().casefold()
    found = next(
        (item for item in newest_first if wanted in chat_file_aliases(item)), None
    )
    if found is None:
        raise SourceFileNotFoundError(
            f"Вложения «{filename}» нет в истории чата. "
            f"Есть (новые первыми): {_addressable_names(newest_first)}"
        )
    return found


def _addressable_names(newest_first: list[Attachment]) -> str:
    names = [chat_file_name(item) for item in newest_first[:LISTED_NAMES_LIMIT]]
    rest = len(newest_first) - len(names)
    listed = ", ".join(names)
    return f"{listed} и ещё {rest}" if rest > 0 else listed
