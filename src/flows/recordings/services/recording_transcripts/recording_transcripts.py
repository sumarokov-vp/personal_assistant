from collections import OrderedDict
from threading import Lock

from src.flows.recordings.services.entities.recorded_transcript import (
    RecordedTranscript,
)

DEFAULT_CAPACITY = 20


class RecordingTranscripts:
    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        self._capacity = capacity
        self._transcripts: OrderedDict[str, RecordedTranscript] = OrderedDict()
        self._lock = Lock()

    def remember(self, transcript: RecordedTranscript) -> None:
        with self._lock:
            self._transcripts[transcript.transcript_id] = transcript
            self._transcripts.move_to_end(transcript.transcript_id)
            while len(self._transcripts) > self._capacity:
                self._transcripts.popitem(last=False)

    def recall(self, transcript_id: str) -> RecordedTranscript | None:
        with self._lock:
            return self._transcripts.get(transcript_id)
