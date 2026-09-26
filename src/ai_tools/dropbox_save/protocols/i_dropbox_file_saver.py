from typing import Protocol


class IDropboxFileSaver(Protocol):
    def save(self, folder: str, name: str, content: bytes) -> str: ...
