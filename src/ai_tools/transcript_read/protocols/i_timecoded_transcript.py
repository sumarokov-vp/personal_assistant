from typing import Protocol


class ITimecodedTranscript(Protocol):
    def parts(self, max_chars: int) -> list[str]: ...
