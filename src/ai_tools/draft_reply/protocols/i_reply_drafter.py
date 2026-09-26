from typing import Protocol

from src.ai_tools.draft_reply.protocols.i_created_draft import ICreatedDraft


class IReplyDrafter(Protocol):
    def create_reply_draft(self, message_id: str, body: str) -> ICreatedDraft: ...
