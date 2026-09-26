from typing import Protocol


class IDocumentTextExtractor(Protocol):
    def extract(self, content: bytes, name: str, max_chars: int) -> str: ...
