from typing import Protocol

from src.ai_tools.file_take.protocols.i_fetched_file import IFetchedFile
from src.files.sources.entities.file_request import FileRequest


class IFileSource(Protocol):
    def fetch(self, request: FileRequest) -> IFetchedFile: ...
