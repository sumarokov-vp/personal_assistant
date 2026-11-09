from pathlib import Path
from typing import Protocol


class IDropboxNewFileBoundary(Protocol):
    def resolve(self, path: str) -> Path: ...

    def write_new_file(self, folder: str, name: str, content: bytes) -> str: ...
