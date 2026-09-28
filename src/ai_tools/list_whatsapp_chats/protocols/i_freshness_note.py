from typing import Protocol


class IFreshnessNote(Protocol):
    def note(self) -> str: ...
