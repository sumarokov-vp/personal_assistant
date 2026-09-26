import io

from pypdf import PdfReader

from src.files.readers.unreadable_format_error import UnreadableFormatError


class PdfTextExtractor:
    def extract(self, content: bytes, name: str, max_chars: int) -> str:
        collected: list[str] = []
        length = 0
        for page in PdfReader(io.BytesIO(content)).pages:
            page_text = page.extract_text() or ""
            collected.append(page_text)
            length += len(page_text)
            if length > max_chars:
                break
        text = "\n\n".join(collected)
        if not text.strip():
            raise UnreadableFormatError(
                f"В {name} нет текстового слоя — похоже на скан, "
                "посмотри его картинкой через file_view"
            )
        return text
