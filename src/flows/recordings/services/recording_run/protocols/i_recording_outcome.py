from typing import Protocol

from src.flows.recordings.services.entities.recorded_transcript import (
    RecordedTranscript,
)


class IRecordingOutcome(Protocol):
    def ready(self, chat_id: int, transcript: RecordedTranscript) -> None: ...

    def failed(self, chat_id: int, file_name: str, reason: str) -> None: ...
