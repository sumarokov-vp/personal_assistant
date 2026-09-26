from typing import Protocol


class IMemoryFillSummary(Protocol):
    def render(self) -> str: ...
