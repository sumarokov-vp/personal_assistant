from src.conversations.errors.conversation_source_error import (
    ConversationSourceError,
)


class AttachmentNotFoundError(ConversationSourceError):
    def __init__(self, message_id: str, attachment_id: str) -> None:
        super().__init__(
            f"В сообщении {message_id} нет вложения {attachment_id}: "
            "возьми attachment_id из списка вложений сообщения"
        )
        self.message_id = message_id
        self.attachment_id = attachment_id
