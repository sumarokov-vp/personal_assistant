from typing import Protocol


class IDropboxWriteBoundary(Protocol):
    def write_new_file(self, folder: str, name: str, content: bytes) -> str: ...
