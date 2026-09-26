from collections.abc import Sequence
from typing import Protocol

from src.ai_tools.search_mail.protocols.i_found_mail import IFoundMail


class IMailSearcher(Protocol):
    def search_messages(self, query: str, limit: int) -> Sequence[IFoundMail]: ...
