from pathlib import PurePosixPath

from ai_framework import Attachment
from ai_framework.entities.attachment import ATTACHMENT_FILE_EXTENSIONS

UNNAMED_PHOTO_PREFIX = "photo_"
KEY_TAIL_LENGTH = 8
EXTENSION_ALIASES = {".jpg": ".jpeg"}


def saved_file_name(attachment: Attachment, requested: str | None) -> str:
    original = attachment.filename or _unnamed(attachment)
    name = (requested or "").strip()
    if not name:
        return original
    if PurePosixPath(name).suffix.casefold() in _own_extensions(attachment):
        return name
    return f"{name}{_extension(attachment)}"


def _unnamed(attachment: Attachment) -> str:
    stem = PurePosixPath(attachment.key or "").stem[:KEY_TAIL_LENGTH]
    return f"{UNNAMED_PHOTO_PREFIX}{stem}{_extension(attachment)}"


def _extension(attachment: Attachment) -> str:
    if attachment.filename and PurePosixPath(attachment.filename).suffix:
        return PurePosixPath(attachment.filename).suffix
    return ATTACHMENT_FILE_EXTENSIONS.get(attachment.media_type, "")


def _own_extensions(attachment: Attachment) -> set[str]:
    extensions = {
        _extension(attachment).casefold(),
        ATTACHMENT_FILE_EXTENSIONS.get(attachment.media_type, "").casefold(),
    }
    aliases = {EXTENSION_ALIASES.get(extension, "") for extension in extensions}
    return (extensions | aliases) - {""}
