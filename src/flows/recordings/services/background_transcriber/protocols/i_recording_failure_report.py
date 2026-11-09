from typing import Protocol


class IRecordingFailureReport(Protocol):
    def failed(self, chat_id: int, file_name: str, reason: str) -> None: ...
