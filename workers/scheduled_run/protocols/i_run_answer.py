from typing import Protocol


class IRunAnswer(Protocol):
    @property
    def content(self) -> str | None: ...
