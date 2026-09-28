from collections.abc import Sequence
from typing import Protocol

from src.gmail.models.mail_summary import MailSummary


class IGmailSearcher(Protocol):
    def search_messages(self, query: str, limit: int) -> Sequence[MailSummary]: ...
