import mimetypes

from src.files.imaging.image_media_type import IMAGE_MEDIA_TYPES
from src.files.imaging.page_selection_error import PageSelectionError
from src.files.imaging.protocols.i_image_fitter import IImageFitter
from src.files.imaging.protocols.i_pdf_rasterizer import IPdfRasterizer
from src.files.imaging.rendered_images import RenderedImages
from src.files.imaging.unviewable_format_error import UnviewableFormatError

PDF_MEDIA_TYPE = "application/pdf"
DEFAULT_PAGE_COUNT = 3
MAX_PAGES_PER_CALL = 5


class FileImageRenderer:
    def __init__(self, fitter: IImageFitter, rasterizer: IPdfRasterizer) -> None:
        self._fitter = fitter
        self._rasterizer = rasterizer

    def render(
        self, content: bytes, media_type: str, name: str, pages: list[int] | None
    ) -> RenderedImages:
        viewable_type = _viewable_media_type(media_type, name)
        if viewable_type == PDF_MEDIA_TYPE:
            return self._render_pdf(content, pages)
        if viewable_type in IMAGE_MEDIA_TYPES:
            return RenderedImages(images=[self._fitter.fit(content, viewable_type)])
        raise UnviewableFormatError(
            f"«{name}» ({media_type}) не картинка и не PDF — его текст читает file_read"
        )

    def _render_pdf(self, content: bytes, pages: list[int] | None) -> RenderedImages:
        page_count = self._rasterizer.page_count(content)
        page_numbers = _select_pages(pages, page_count)
        rendered = self._rasterizer.render_png(content, page_numbers)
        images = [
            self._fitter.fit(png, "image/png").model_copy(update={"page": number})
            for number, png in zip(page_numbers, rendered, strict=True)
        ]
        return RenderedImages(images=images, page_count=page_count)


def _viewable_media_type(media_type: str, name: str) -> str:
    if media_type == PDF_MEDIA_TYPE or media_type in IMAGE_MEDIA_TYPES:
        return media_type
    guessed, _ = mimetypes.guess_type(name)
    return guessed or media_type


def _select_pages(pages: list[int] | None, page_count: int) -> list[int]:
    if not pages:
        return list(range(1, min(DEFAULT_PAGE_COUNT, page_count) + 1))
    selected = list(dict.fromkeys(pages))
    if len(selected) > MAX_PAGES_PER_CALL:
        raise PageSelectionError(
            f"За вызов — не больше {MAX_PAGES_PER_CALL} страниц, запрошено {len(selected)}"
        )
    outside = [number for number in selected if not 1 <= number <= page_count]
    if outside:
        raise PageSelectionError(
            f"В документе {page_count} стр., страниц {outside} нет"
        )
    return selected
