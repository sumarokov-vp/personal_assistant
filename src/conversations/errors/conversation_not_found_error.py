from src.conversations.errors.conversation_source_error import (
    ConversationSourceError,
)


class ConversationNotFoundError(ConversationSourceError):
    def __init__(self, conversation_id: str) -> None:
        super().__init__(f"Переписки {conversation_id} нет в источнике")
        self.conversation_id = conversation_id
