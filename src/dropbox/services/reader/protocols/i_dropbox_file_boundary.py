from typing import BinaryIO, Protocol


class IDropboxFileBoundary(Protocol):
    def open_read(self, path: str) -> BinaryIO: ...
