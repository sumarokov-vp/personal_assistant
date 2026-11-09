from typing import Protocol

from src.flows.recordings.services.entities.recorded_transcript import (
    RecordedTranscript,
)


class ITranscriptRecall(Protocol):
    def recall(self, transcript_id: str) -> RecordedTranscript | None: ...
