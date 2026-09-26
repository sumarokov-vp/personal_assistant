from typing import BinaryIO, Protocol

from src.files.readers.extracted_text import ExtractedText


class IFileTextReader(Protocol):
    def read(self, stream: BinaryIO, name: str) -> ExtractedText: ...
