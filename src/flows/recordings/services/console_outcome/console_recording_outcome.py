from collections.abc import Callable

from src.flows.recordings.services.recording_links.recording_links import (
    RecordingLinks,
)


class ConsoleRecordingOutcome:
    def __init__(self, links: RecordingLinks, write: Callable[[str], None]) -> None:
        self._links = links
        self._write = write
        self.transcript_path: str | None = None

    def ready(self, chat_id: int, file_name: str, transcript_path: str) -> None:
        self.transcript_path = transcript_path
        self._write(f"ok: {file_name} -> {transcript_path}")
        self._write(f"link: {self._links.transcript_url(transcript_path)}")
        for prompt in self._links.protocol_prompts(transcript_path):
            self._write(f"button «{prompt.title}»: {prompt.url}")

    def failed(self, chat_id: int, file_name: str, reason: str) -> None:
        self._write(f"failed: {file_name}: {reason}")
