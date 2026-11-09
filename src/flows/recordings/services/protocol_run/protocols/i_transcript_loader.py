from typing import Protocol

from src.flows.recordings.services.entities.protocol_request import ProtocolRequest
from src.flows.recordings.services.entities.recorded_transcript import (
    RecordedTranscript,
)


class ITranscriptLoader(Protocol):
    def load(self, request: ProtocolRequest) -> RecordedTranscript: ...
