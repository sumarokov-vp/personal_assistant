from typing import Protocol


class IRecordingDownloader(Protocol):
    def download_document(self, file_id: str) -> bytes: ...
