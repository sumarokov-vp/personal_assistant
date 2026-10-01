from typing import Protocol


class ITextSplitter(Protocol):
    def split(self, text: str) -> list[str]: ...
