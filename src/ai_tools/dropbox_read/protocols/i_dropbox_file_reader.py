from typing import Protocol

from src.dropbox.services.reader.file_text import FileText


class IDropboxFileReader(Protocol):
    def read(self, path: str) -> FileText: ...
