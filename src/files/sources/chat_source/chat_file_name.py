from pathlib import PurePosixPath

from ai_framework import Attachment
from ai_framework.entities.attachment import ATTACHMENT_FILE_EXTENSIONS

UNNAMED_PHOTO_PREFIX = "photo_"
KEY_TAIL_LENGTH = 8


def chat_file_name(attachment: Attachment) -> str:
    if attachment.filename:
        return attachment.filename
    stem = PurePosixPath(attachment.key or "").stem[:KEY_TAIL_LENGTH]
    extension = ATTACHMENT_FILE_EXTENSIONS.get(attachment.media_type, "")
    return f"{UNNAMED_PHOTO_PREFIX}{stem}{extension}"
