from typing import Any, Protocol

from src.ai_tools.transcript_read.protocols.i_timecoded_transcript import (
    ITimecodedTranscript,
)


class ITimecodedTranscriptFactory(Protocol):
    def __call__(self, result: dict[str, Any]) -> ITimecodedTranscript: ...
