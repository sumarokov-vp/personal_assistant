from typing import Protocol


class IConversationClearer(Protocol):
    def clear_context(self, thread_id: str) -> None: ...
