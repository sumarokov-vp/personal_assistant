from pathlib import Path
from typing import BinaryIO, Protocol


class IDropboxFileReader(Protocol):
    @property
    def root(self) -> Path: ...

    def open_read(self, path: str) -> BinaryIO: ...
