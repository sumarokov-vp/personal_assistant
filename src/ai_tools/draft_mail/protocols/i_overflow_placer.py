from typing import Protocol

from src.ai_tools.draft_mail.protocols.i_draft_work_file import IDraftWorkFile


class IOverflowPlacer[WorkFileT: IDraftWorkFile](Protocol):
    def place(self, work_file: WorkFileT) -> str: ...
