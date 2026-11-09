from collections.abc import Sequence

from src.flows.recordings.services import RecordedTranscript
from src.flows.recordings.services.recording_run.protocols import IRecordingOutcome


class FanOutRecordingOutcome:
    def __init__(self, outcomes: Sequence[IRecordingOutcome]) -> None:
        self._outcomes = list(outcomes)

    def ready(self, chat_id: int, transcript: RecordedTranscript) -> None:
        for outcome in self._outcomes:
            outcome.ready(chat_id, transcript)

    def failed(self, chat_id: int, file_name: str, reason: str) -> None:
        for outcome in self._outcomes:
            outcome.failed(chat_id, file_name, reason)
