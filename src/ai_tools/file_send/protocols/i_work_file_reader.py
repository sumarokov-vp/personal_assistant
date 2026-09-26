from typing import Protocol

from src.files.work_folder.work_file import WorkFile


class IWorkFileReader(Protocol):
    def get(self, file_id: str) -> WorkFile: ...

    def read(self, file_id: str) -> bytes: ...
