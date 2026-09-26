import io
import os
from collections.abc import Iterable
from pathlib import PurePosixPath
from typing import BinaryIO

from pypdf import PageObject, PdfReader

from src.dropbox.services.reader.file_text import FileText
from src.dropbox.services.reader.protocols.i_dropbox_file_boundary import (
    IDropboxFileBoundary,
)
from src.dropbox.services.reader.unreadable_format_error import UnreadableFormatError

TEXT_SUFFIXES = (".txt", ".md", ".csv", ".json")
PDF_SUFFIX = ".pdf"
DEFAULT_MAX_TEXT_CHARS = 40_000
DEFAULT_MAX_PDF_BYTES = 30 * 1024 * 1024


class DropboxReader:
    def __init__(
        self,
        boundary: IDropboxFileBoundary,
        max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
        max_pdf_bytes: int = DEFAULT_MAX_PDF_BYTES,
    ) -> None:
        self._boundary = boundary
        self._max_text_chars = max_text_chars
        self._max_pdf_bytes = max_pdf_bytes

    def read(self, path: str) -> FileText:
        suffix = PurePosixPath(path).suffix.casefold()
        with self._boundary.open_read(path) as file:
            _ensure_readable_format(suffix)
            text = (
                self._pdf_text(file, path)
                if suffix == PDF_SUFFIX
                else self._plain_text(file)
            )
        return FileText(
            path=path,
            text=text[: self._max_text_chars],
            truncated=len(text) > self._max_text_chars,
        )

    def _plain_text(self, file: BinaryIO) -> str:
        max_bytes = self._max_text_chars * 4 + 4
        return file.read(max_bytes).decode("utf-8", errors="replace")

    def _pdf_text(self, file: BinaryIO, path: str) -> str:
        size = os.fstat(file.fileno()).st_size
        if size > self._max_pdf_bytes:
            raise UnreadableFormatError(
                f"{path} весит {size // (1024 * 1024)} МБ — PDF больше "
                f"{self._max_pdf_bytes // (1024 * 1024)} МБ не читается"
            )
        pages = PdfReader(io.BytesIO(file.read())).pages
        text = self._collect_pages(pages)
        if not text.strip():
            raise UnreadableFormatError(
                f"В {path} нет текстового слоя (похоже на скан) — такой PDF не читается"
            )
        return text

    def _collect_pages(self, pages: Iterable[PageObject]) -> str:
        collected: list[str] = []
        length = 0
        for page in pages:
            page_text = page.extract_text() or ""
            collected.append(page_text)
            length += len(page_text)
            if length > self._max_text_chars:
                break
        return "\n\n".join(collected)


def _ensure_readable_format(suffix: str) -> None:
    if suffix not in (*TEXT_SUFFIXES, PDF_SUFFIX):
        raise UnreadableFormatError(
            f"Формат {suffix or 'без расширения'} не читается: доступны только "
            "txt, md, csv, json и текст PDF"
        )
