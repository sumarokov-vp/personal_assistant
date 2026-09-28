from typing import Protocol

from src.conversations.models.conversation import Conversation
from src.conversations.models.conversation_message import ConversationMessage
from src.conversations.models.conversation_window import ConversationWindow


class IConversationReader(Protocol):
    def read_message(self, message_id: str) -> ConversationMessage: ...

    def read_conversation(
        self, conversation_id: str, window: ConversationWindow
    ) -> Conversation: ...
