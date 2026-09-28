from collections.abc import Sequence
from typing import Protocol

from src.conversations.models.conversation_summary import ConversationSummary


class IConversationDirectory(Protocol):
    def list_conversations(
        self, title_contains: str | None, limit: int
    ) -> Sequence[ConversationSummary]: ...
