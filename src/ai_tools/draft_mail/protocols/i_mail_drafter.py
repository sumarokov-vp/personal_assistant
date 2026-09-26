from collections.abc import Sequence
from typing import Protocol

from src.ai_tools.draft_mail.protocols.i_created_draft import ICreatedDraft
from src.ai_tools.draft_mail.protocols.i_draft_file import IDraftFile


class IMailDrafter(Protocol):
    def create_draft(
        self,
        recipient: str,
        subject: str,
        body: str,
        attachments: Sequence[IDraftFile],
    ) -> ICreatedDraft: ...
