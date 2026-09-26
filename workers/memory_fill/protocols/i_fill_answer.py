from typing import Protocol


class IFillAnswer(Protocol):
    @property
    def content(self) -> str | None: ...
