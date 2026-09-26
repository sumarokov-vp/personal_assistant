import io

import pypdfium2 as pdfium

POINTS_PER_INCH = 72


class PdfRasterizer:
    def __init__(self, dpi: int) -> None:
        self._scale = dpi / POINTS_PER_INCH

    def page_count(self, content: bytes) -> int:
        document = pdfium.PdfDocument(content)
        count = len(document)
        document.close()
        return count

    def render_png(self, content: bytes, page_numbers: list[int]) -> list[bytes]:
        document = pdfium.PdfDocument(content)
        rendered = [self._render_page(document, number) for number in page_numbers]
        document.close()
        return rendered

    def _render_page(self, document: pdfium.PdfDocument, page_number: int) -> bytes:
        page = document[page_number - 1]
        bitmap = page.render(scale=self._scale)
        image = bitmap.to_pil()
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        bitmap.close()
        page.close()
        return buffer.getvalue()
