from pathlib import Path


class LocalRecordingSource:
    def download_document(self, file_id: str) -> bytes:
        return Path(file_id).read_bytes()
