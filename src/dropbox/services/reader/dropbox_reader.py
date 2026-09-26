from pathlib import PurePosixPath

from src.dropbox.services.reader.file_text import FileText
from src.dropbox.services.reader.protocols.i_dropbox_file_boundary import (
    IDropboxFileBoundary,
)
from src.dropbox.services.reader.protocols.i_file_text_reader import IFileTextReader
from src.files.readers.file_text_reader import FileTextReader


class DropboxReader:
    def __init__(
        self,
        boundary: IDropboxFileBoundary,
        text_reader: IFileTextReader | None = None,
    ) -> None:
        self._boundary = boundary
        self._text_reader = text_reader or FileTextReader()

    def read(self, path: str) -> FileText:
        with self._boundary.open_read(path) as file:
            extracted = self._text_reader.read(file, PurePosixPath(path).name)
        return FileText(path=path, text=extracted.text, truncated=extracted.truncated)
