from src.conversations.errors.conversation_source_error import (
    ConversationSourceError,
)


class AttachmentNotDownloadedError(ConversationSourceError):
    def __init__(self, name: str, hint: str) -> None:
        super().__init__(f"Файла «{name}» нет на диске источника: {hint}")
        self.name = name
        self.hint = hint
