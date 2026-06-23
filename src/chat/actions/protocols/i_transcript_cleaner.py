from typing import Protocol


class ITranscriptCleaner(Protocol):
    def clean(self, raw_text: str) -> str: ...
