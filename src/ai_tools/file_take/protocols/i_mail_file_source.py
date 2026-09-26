from typing import Protocol

from src.ai_tools.file_take.protocols.i_fetched_file import IFetchedFile


class IMailFileSource(Protocol):
    def fetch(self, message_id: str, attachment_id: str) -> IFetchedFile: ...
