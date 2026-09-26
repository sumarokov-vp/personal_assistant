from typing import Protocol

from src.ai_tools.file_take.protocols.i_fetched_file import IFetchedFile


class IDropboxFileSource(Protocol):
    def fetch(self, path: str) -> IFetchedFile: ...
