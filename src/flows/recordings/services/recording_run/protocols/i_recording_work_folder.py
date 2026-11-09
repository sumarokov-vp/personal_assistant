from pathlib import Path
from typing import Protocol

from src.files.work_folder.work_file import WorkFile


class IRecordingWorkFolder(Protocol):
    def put(
        self, content: bytes, name: str, media_type: str, source: str
    ) -> WorkFile: ...

    def path(self, file_id: str) -> Path: ...

    def remove(self, file_id: str) -> None: ...
