from typing import Protocol


class IOwnerNotifier(Protocol):
    def notify(self, text: str) -> None: ...
