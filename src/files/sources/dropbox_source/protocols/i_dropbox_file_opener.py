from typing import BinaryIO, Protocol


class IDropboxFileOpener(Protocol):
    def open_read(self, path: str) -> BinaryIO: ...
