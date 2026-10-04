from typing import Protocol

from src.knowledge_intake.models.mailbox_folder import MailboxFolder
from src.knowledge_intake.models.raw_letter import RawLetter


class IMailbox(Protocol):
    def unread(self) -> list[RawLetter]: ...

    def move(self, uid: str, folder: MailboxFolder) -> None: ...
