from typing import Protocol


class ICheckupAnswer(Protocol):
    @property
    def content(self) -> str | None: ...
