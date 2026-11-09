from secrets import token_hex
from threading import Lock

from src.flows.recordings.handlers.pending.pending_recording import PendingRecording
from src.flows.recordings.handlers.recording_file import RecordingFile

INTAKE_ID_BYTES = 8


class PendingRecordings:
    def __init__(self) -> None:
        self._waiting: dict[str, PendingRecording] = {}
        self._answered: set[str] = set()
        self._lock = Lock()

    def add(self, chat_id: int, recording: RecordingFile) -> PendingRecording:
        pending = PendingRecording(
            intake_id=token_hex(INTAKE_ID_BYTES), chat_id=chat_id, recording=recording
        )
        with self._lock:
            self._waiting[pending.intake_id] = pending
        return pending

    def take(self, intake_id: str) -> PendingRecording | None:
        with self._lock:
            pending = self._waiting.pop(intake_id, None)
            if pending is not None:
                self._answered.add(intake_id)
            return pending

    def was_answered(self, intake_id: str) -> bool:
        with self._lock:
            return intake_id in self._answered
