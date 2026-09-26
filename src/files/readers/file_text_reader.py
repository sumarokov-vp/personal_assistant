from pathlib import PurePosixPath
from typing import BinaryIO

from src.files.readers.extracted_text import ExtractedText
from src.files.readers.extractors.docx_text_extractor import DocxTextExtractor
from src.files.readers.extractors.pdf_text_extractor import PdfTextExtractor
from src.files.readers.extractors.xlsx_text_extractor import XlsxTextExtractor
from src.files.readers.protocols.i_document_text_extractor import (
    IDocumentTextExtractor,
)
from src.files.readers.unreadable_format_error import UnreadableFormatError

PLAIN_TEXT_SUFFIXES = (".txt", ".md", ".csv", ".json")
READABLE_FORMATS = "txt, md, csv, json, pdf (текстовый слой), docx, xlsx"
DEFAULT_MAX_TEXT_CHARS = 40_000
DEFAULT_MAX_DOCUMENT_BYTES = 30 * 1024 * 1024
BYTES_PER_CHAR_CEILING = 4
MEGABYTE = 1024 * 1024


class FileTextReader:
    def __init__(
        self,
        max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
        max_document_bytes: int = DEFAULT_MAX_DOCUMENT_BYTES,
    ) -> None:
        self._max_text_chars = max_text_chars
        self._max_document_bytes = max_document_bytes
        self._document_extractors: dict[str, IDocumentTextExtractor] = {
            ".pdf": PdfTextExtractor(),
            ".docx": DocxTextExtractor(),
            ".xlsx": XlsxTextExtractor(),
        }

    def read(self, stream: BinaryIO, name: str) -> ExtractedText:
        suffix = PurePosixPath(name).suffix.casefold()
        if suffix in PLAIN_TEXT_SUFFIXES:
            text = self._plain_text(stream)
        elif suffix in self._document_extractors:
            text = self._document_text(stream, name, self._document_extractors[suffix])
        else:
            raise UnreadableFormatError(
                f"Формат {suffix or 'без расширения'} не читается: "
                f"доступны {READABLE_FORMATS}"
            )
        return ExtractedText(
            text=text[: self._max_text_chars],
            truncated=len(text) > self._max_text_chars,
        )

    def _plain_text(self, stream: BinaryIO) -> str:
        max_bytes = (
            self._max_text_chars * BYTES_PER_CHAR_CEILING + BYTES_PER_CHAR_CEILING
        )
        return stream.read(max_bytes).decode("utf-8", errors="replace")

    def _document_text(
        self, stream: BinaryIO, name: str, extractor: IDocumentTextExtractor
    ) -> str:
        content = stream.read(self._max_document_bytes + 1)
        if len(content) > self._max_document_bytes:
            raise UnreadableFormatError(
                f"{name} больше {self._max_document_bytes // MEGABYTE} МБ — "
                "такой документ не читается"
            )
        return extractor.extract(content, name, self._max_text_chars)
