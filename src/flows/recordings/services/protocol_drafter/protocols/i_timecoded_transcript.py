from typing import Protocol


class ITimecodedTranscript(Protocol):
    @property
    def text(self) -> str: ...

    def parts(self, max_chars: int) -> list[str]: ...
