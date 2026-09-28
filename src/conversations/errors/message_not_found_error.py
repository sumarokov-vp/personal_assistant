from src.conversations.errors.conversation_source_error import (
    ConversationSourceError,
)


class MessageNotFoundError(ConversationSourceError):
    def __init__(self, message_id: str) -> None:
        super().__init__(f"Сообщения {message_id} нет в источнике")
        self.message_id = message_id
