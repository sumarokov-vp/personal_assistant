from typing import Protocol

from src.gmail.models.mail_attachment_file import MailAttachmentFile
from src.gmail.models.mail_message import MailMessage
from src.gmail.services.conversation_source.protocols.i_gmail_reader import (
    IGmailReader,
)
from src.gmail.services.conversation_source.protocols.i_gmail_searcher import (
    IGmailSearcher,
)


class IGmailMailbox(IGmailSearcher, IGmailReader, Protocol):
    def get_thread(self, thread_id: str) -> list[MailMessage]: ...

    def search_thread_message_ids(self, thread_id: str, query: str) -> set[str]: ...

    def get_attachment_file(
        self, message_id: str, attachment_id: str
    ) -> MailAttachmentFile: ...
