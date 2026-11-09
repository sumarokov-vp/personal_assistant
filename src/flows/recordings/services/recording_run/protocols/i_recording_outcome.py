from typing import Protocol


class IRecordingOutcome(Protocol):
    def ready(self, chat_id: int, file_name: str, transcript_path: str) -> None: ...

    def failed(self, chat_id: int, file_name: str, reason: str) -> None: ...
