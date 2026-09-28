import mimetypes
import re
from pathlib import Path, PurePosixPath

from src.conversations.models.conversation_attachment import ConversationAttachment
from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow
from src.whatsapp.macos_desktop.services.attachment_describer.media_kind import (
    DOCUMENT_MESSAGE_TYPE,
    FALLBACK_KIND,
    KIND_BY_MESSAGE_TYPE,
    MediaKind,
)

FILE_SUFFIX = re.compile(r"\.[A-Za-z0-9]{1,8}")
MAX_FILE_NAME_LENGTH = 255


class AttachmentDescriber:
    def __init__(self, media_root: Path) -> None:
        self._media_root = media_root

    def describe(self, row: WhatsAppMessageRow) -> ConversationAttachment | None:
        if not row.has_attachment or row.media_pk is None:
            return None
        local_file = self.local_file(row)
        name = self._name(row)
        size = row.media_size if row.media_size else None
        if size is None and local_file is not None:
            size = local_file.stat().st_size
        return ConversationAttachment(
            attachment_id=str(row.media_pk),
            name=name,
            media_type=self._media_type(name, self._kind(row)),
            size=size,
            downloaded=local_file is not None,
        )

    def local_file(self, row: WhatsAppMessageRow) -> Path | None:
        if not row.media_path:
            return None
        root = self._media_root.resolve()
        candidate = (root / row.media_path).resolve()
        if not candidate.is_relative_to(root) or not candidate.is_file():
            return None
        return candidate

    def _name(self, row: WhatsAppMessageRow) -> str:
        if row.message_type == DOCUMENT_MESSAGE_TYPE:
            for candidate in (row.media_title, row.body):
                if candidate and _looks_like_file_name(candidate):
                    return candidate
        kind = self._kind(row)
        suffix = PurePosixPath(row.media_path).suffix if row.media_path else kind.suffix
        return f"whatsapp-{kind.label}-{row.media_pk}{suffix}"

    def _kind(self, row: WhatsAppMessageRow) -> MediaKind:
        if row.message_type is None:
            return FALLBACK_KIND
        return KIND_BY_MESSAGE_TYPE.get(row.message_type, FALLBACK_KIND)

    def _media_type(self, name: str, kind: MediaKind) -> str:
        guessed, _ = mimetypes.guess_type(name, strict=False)
        return guessed or kind.media_type


def _looks_like_file_name(candidate: str) -> bool:
    return (
        len(candidate) <= MAX_FILE_NAME_LENGTH
        and "\n" not in candidate
        and "/" not in candidate
        and FILE_SUFFIX.fullmatch(PurePosixPath(candidate).suffix) is not None
    )
