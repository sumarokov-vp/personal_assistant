from typing import Protocol

from src.files.sources.entities.fetched_file import FetchedFile
from src.files.sources.entities.file_request import FileRequest


class IFileSource(Protocol):
    def fetch(self, request: FileRequest) -> FetchedFile: ...
