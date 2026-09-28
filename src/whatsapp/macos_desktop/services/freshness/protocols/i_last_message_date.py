from typing import Protocol


class ILastMessageDate(Protocol):
    def last_message_seconds(self) -> float | None: ...
