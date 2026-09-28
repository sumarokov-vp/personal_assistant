import mimetypes
from pathlib import PurePosixPath

from src.files.sources.dropbox_source.protocols.i_dropbox_file_opener import (
    IDropboxFileOpener,
)
from src.files.sources.entities.fetched_file import FetchedFile
from src.files.sources.entities.file_request import FileRequest
from src.files.sources.entities.file_request_incomplete_error import (
    FileRequestIncompleteError,
)
from src.files.sources.entities.source_file_too_large_error import (
    SourceFileTooLargeError,
)

UNKNOWN_MEDIA_TYPE = "application/octet-stream"


class DropboxFileSource:
    def __init__(self, boundary: IDropboxFileOpener, max_bytes: int) -> None:
        self._boundary = boundary
        self._max_bytes = max_bytes

    def fetch(self, request: FileRequest) -> FetchedFile:
        path = (request.path or "").strip()
        if not path:
            raise FileRequestIncompleteError(
                "Для файла Dropbox нужен path относительно корня Dropbox"
            )
        name = PurePosixPath(path).name
        with self._boundary.open_read(path) as file:
            content = file.read(self._max_bytes + 1)
        if len(content) > self._max_bytes:
            raise SourceFileTooLargeError(name, self._max_bytes)
        media_type, _ = mimetypes.guess_type(name)
        return FetchedFile(
            content=content,
            name=name,
            media_type=media_type or UNKNOWN_MEDIA_TYPE,
            origin=f"dropbox:{path}",
        )
