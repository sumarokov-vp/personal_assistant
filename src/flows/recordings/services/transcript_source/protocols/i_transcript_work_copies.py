from pathlib import Path
from typing import Protocol

from src.files.work_folder.work_file import WorkFile


class ITranscriptWorkCopies(Protocol):
    def get(self, file_id: str) -> WorkFile: ...

    def path(self, file_id: str) -> Path: ...
