from typing import Protocol


class IWorkFileContent(Protocol):
    def read(self, file_id: str) -> bytes: ...
