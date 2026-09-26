from typing import Protocol


class IExtractedText(Protocol):
    @property
    def text(self) -> str: ...

    @property
    def truncated(self) -> bool: ...
