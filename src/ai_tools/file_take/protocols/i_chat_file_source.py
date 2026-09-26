from typing import Protocol

from src.ai_tools.file_take.protocols.i_fetched_file import IFetchedFile


class IChatFileSource(Protocol):
    def fetch(self, thread_id: str, filename: str | None) -> IFetchedFile: ...
