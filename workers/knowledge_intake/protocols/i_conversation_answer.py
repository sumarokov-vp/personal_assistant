from typing import Protocol


class IConversationAnswer(Protocol):
    @property
    def content(self) -> str | None: ...
