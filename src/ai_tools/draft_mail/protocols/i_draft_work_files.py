from typing import Protocol

from src.ai_tools.draft_mail.protocols.i_draft_work_file import IDraftWorkFile


class IDraftWorkFiles[WorkFileT: IDraftWorkFile](Protocol):
    def get(self, file_id: str) -> WorkFileT: ...

    def read(self, file_id: str) -> bytes: ...
