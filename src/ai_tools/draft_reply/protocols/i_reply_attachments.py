from collections.abc import Sequence
from typing import Protocol

from src.ai_tools.draft_reply.protocols.i_reply_file import IReplyFile


class IReplyAttachments(Protocol):
    def collect(self, file_ids: Sequence[str]) -> Sequence[IReplyFile]: ...

    def settle(
        self,
        files: Sequence[IReplyFile],
        attached: Sequence[str],
        left_out: Sequence[str],
    ) -> list[str]: ...
