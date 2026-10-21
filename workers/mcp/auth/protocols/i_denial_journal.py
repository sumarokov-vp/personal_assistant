from typing import Protocol


class IDenialJournal(Protocol):
    def record_denied(self, user: str | None) -> None: ...
