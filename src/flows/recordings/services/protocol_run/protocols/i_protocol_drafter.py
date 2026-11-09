from typing import Protocol

from src.flows.recordings.services.entities.recorded_transcript import (
    RecordedTranscript,
)
from src.protocols.models.protocol_content import ProtocolContent
from src.protocols.models.protocol_kind import ProtocolKind


class IProtocolDrafter(Protocol):
    def draft(
        self, kind: ProtocolKind, transcript: RecordedTranscript
    ) -> ProtocolContent: ...
