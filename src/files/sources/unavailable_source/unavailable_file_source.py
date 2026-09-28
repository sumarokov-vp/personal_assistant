from src.files.sources.entities.fetched_file import FetchedFile
from src.files.sources.entities.file_request import FileRequest
from src.files.sources.entities.file_source_unavailable_error import (
    FileSourceUnavailableError,
)


class UnavailableFileSource:
    def __init__(self, reason: str) -> None:
        self._reason = reason

    def fetch(self, request: FileRequest) -> FetchedFile:
        raise FileSourceUnavailableError(self._reason)
