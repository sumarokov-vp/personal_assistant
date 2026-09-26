from typing import Protocol

from src.files.work_folder.work_file import WorkFile


class IOverflowFolder(Protocol):
    def place(self, work_file: WorkFile) -> str: ...
