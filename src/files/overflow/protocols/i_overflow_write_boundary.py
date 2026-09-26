from typing import Protocol


class IOverflowWriteBoundary(Protocol):
    def write_new_file(self, folder: str, name: str, content: bytes) -> str: ...
