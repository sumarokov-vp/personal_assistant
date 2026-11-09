from typing import Protocol


class ITranscriptsStorage(Protocol):
    def write_new_file(self, folder: str, name: str, content: bytes) -> str: ...
