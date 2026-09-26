from typing import Protocol


class IDropboxMoveBoundary(Protocol):
    def move_denial(self, source: str, target: str) -> str | None: ...

    def move(self, source: str, target: str) -> str: ...
