from typing import Protocol

from src.conversations.models.conversation_message import ConversationMessage


class IMessageReader(Protocol):
    def read_message(self, message_id: str) -> ConversationMessage: ...
