from typing import Protocol

from src.flows.recordings.services.entities.recorded_transcript import (
    RecordedTranscript,
)


class ITranscriptMemory(Protocol):
    def remember(self, transcript: RecordedTranscript) -> None: ...
