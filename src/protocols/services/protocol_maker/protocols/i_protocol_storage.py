from typing import Protocol


class IProtocolStorage(Protocol):
    @property
    def folder(self) -> str: ...

    def write_new_file(self, path: str, content: bytes) -> str: ...
