from typing import Protocol


class IDropboxMover(Protocol):
    def move(self, source: str, target: str) -> str: ...
