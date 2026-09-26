from typing import Protocol

from src.ai_tools.file_read.protocols.i_work_file_info import IWorkFileInfo


class IWorkFileReader(Protocol):
    def get(self, file_id: str) -> IWorkFileInfo: ...

    def read(self, file_id: str) -> bytes: ...
