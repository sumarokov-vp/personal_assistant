from collections.abc import Sequence
from typing import Protocol

from src.conversations.models.message_query import MessageQuery
from src.conversations.models.message_summary import MessageSummary


class IMessageSearch(Protocol):
    def search(self, query: MessageQuery) -> Sequence[MessageSummary]: ...
