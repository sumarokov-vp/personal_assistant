from typing import BinaryIO, Protocol

from src.ai_tools.file_read.protocols.i_extracted_text import IExtractedText


class IFileTextReader(Protocol):
    def read(self, stream: BinaryIO, name: str) -> IExtractedText: ...
