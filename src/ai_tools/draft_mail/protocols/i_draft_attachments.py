from collections.abc import Sequence
from typing import Protocol

from src.ai_tools.draft_mail.protocols.i_draft_file import IDraftFile


class IDraftAttachments(Protocol):
    def collect(self, file_ids: Sequence[str]) -> Sequence[IDraftFile]: ...

    def settle(
        self,
        files: Sequence[IDraftFile],
        attached: Sequence[str],
        left_out: Sequence[str],
    ) -> list[str]: ...
