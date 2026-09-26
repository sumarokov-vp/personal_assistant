from collections.abc import Sequence
from typing import Protocol

from src.ai_tools.draft_reply.protocols.i_created_draft import ICreatedDraft
from src.ai_tools.draft_reply.protocols.i_reply_file import IReplyFile


class IReplyDrafter(Protocol):
    def create_reply_draft(
        self, message_id: str, body: str, attachments: Sequence[IReplyFile]
    ) -> ICreatedDraft: ...
