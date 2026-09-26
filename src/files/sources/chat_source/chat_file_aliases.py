from pathlib import PurePosixPath

from ai_framework import Attachment

from src.files.sources.chat_source.chat_file_name import chat_file_name


def chat_file_aliases(attachment: Attachment) -> set[str]:
    aliases = {chat_file_name(attachment)}
    if attachment.key:
        key = PurePosixPath(attachment.key)
        aliases.update({attachment.key, key.name, key.stem})
    return {alias.casefold() for alias in aliases}
