from typing import BinaryIO, Protocol


class IStorageFileOpener(Protocol):
    def open_read(self, path: str) -> BinaryIO: ...
