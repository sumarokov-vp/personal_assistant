from typing import Protocol


class IDateDisplay(Protocol):
    def display(self, seconds: float | None) -> str: ...
