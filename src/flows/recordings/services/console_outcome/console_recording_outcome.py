from collections.abc import Callable

from src.flows.recordings.services.entities.protocol_callback import ProtocolCallback
from src.flows.recordings.services.entities.recorded_transcript import (
    RecordedTranscript,
)
from src.flows.recordings.services.recording_links.recording_links import (
    RecordingLinks,
)


class ConsoleRecordingOutcome:
    def __init__(
        self,
        links: RecordingLinks,
        protocol_callback: ProtocolCallback,
        write: Callable[[str], None],
    ) -> None:
        self._links = links
        self._protocol_callback = protocol_callback
        self._write = write
        self.transcript: RecordedTranscript | None = None

    def ready(self, chat_id: int, transcript: RecordedTranscript) -> None:
        self.transcript = transcript
        self._write(f"ok: {transcript.recording_name} -> {transcript.transcript_path}")
        self._write(f"link: {self._links.transcript_url(transcript.transcript_path)}")
        for button in self._protocol_callback.buttons(transcript.transcript_id):
            self._write(f"button «{button.text}»: {button.data}")

    def failed(self, chat_id: int, file_name: str, reason: str) -> None:
        self._write(f"failed: {file_name}: {reason}")
