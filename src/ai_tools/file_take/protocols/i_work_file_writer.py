from typing import Protocol

from src.ai_tools.file_take.protocols.i_taken_work_file import ITakenWorkFile


class IWorkFileWriter(Protocol):
    def put(
        self, content: bytes, name: str, media_type: str, source: str
    ) -> ITakenWorkFile: ...
