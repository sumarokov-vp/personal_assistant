from typing import Protocol


class IDropboxMoveChecker(Protocol):
    def move_denial(self, source: str, target: str) -> str | None: ...
