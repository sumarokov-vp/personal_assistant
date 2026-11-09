from typing import Protocol

from src.flows.recordings.services.entities.recording_request import RecordingRequest


class IRecordingRun(Protocol):
    def run(self, request: RecordingRequest) -> None: ...
