import base64
import io
import os

import pytest
from PIL import Image

from src.files.imaging import (
    FileImageRenderer,
    ImageFitter,
    PageSelectionError,
    PdfRasterizer,
    UnviewableFormatError,
)

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MEGABYTE = 1024 * 1024


def renderer() -> FileImageRenderer:
    return FileImageRenderer(
        fitter=ImageFitter(MAX_IMAGE_BYTES), rasterizer=PdfRasterizer(150)
    )


def noise_image(width: int, height: int) -> Image.Image:
    return Image.frombytes("RGB", (width, height), os.urandom(width * height * 3))


def encoded(image: Image.Image, image_format: str, **options: int) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=image_format, **options)
    return buffer.getvalue()


def blank_scan_pdf(pages: int) -> bytes:
    sheets = [Image.new("RGB", (620, 877), "white") for _ in range(pages)]
    buffer = io.BytesIO()
    sheets[0].save(
        buffer, format="PDF", save_all=True, append_images=sheets[1:], resolution=75
    )
    return buffer.getvalue()


def test_png_within_limit_passes_unchanged() -> None:
    png = encoded(noise_image(600, 600), "PNG")
    assert MEGABYTE <= len(png) < 2 * MEGABYTE

    rendered = renderer().render(png, "image/png", "scan.png", None)

    assert len(rendered.images) == 1
    assert rendered.images[0].media_type == "image/png"
    assert rendered.images[0].data == png
    assert rendered.images[0].reduced is False


def test_large_jpeg_is_reduced_under_base64_limit() -> None:
    jpeg = encoded(noise_image(3600, 3600), "JPEG", quality=95)
    assert len(jpeg) >= 12 * MEGABYTE

    rendered = renderer().render(jpeg, "image/jpeg", "photo.jpg", None)

    image = rendered.images[0]
    assert image.reduced is True
    assert image.media_type == "image/jpeg"
    assert len(base64.standard_b64encode(image.data)) <= MAX_IMAGE_BYTES
    assert max(Image.open(io.BytesIO(image.data)).size) <= 1568


def test_textless_pdf_becomes_png_per_page() -> None:
    rendered = renderer().render(blank_scan_pdf(3), "application/pdf", "scan.pdf", None)

    assert rendered.page_count == 3
    assert [image.page for image in rendered.images] == [1, 2, 3]
    assert all(image.media_type == "image/png" for image in rendered.images)
    assert all(image.data.startswith(b"\x89PNG") for image in rendered.images)


def test_pdf_shows_first_three_pages_by_default_and_requested_ones_on_demand() -> None:
    pdf = blank_scan_pdf(7)

    assert [
        image.page
        for image in renderer().render(pdf, "application/pdf", "a.pdf", None).images
    ] == [1, 2, 3]
    assert [
        image.page
        for image in renderer().render(pdf, "application/pdf", "a.pdf", [7, 5]).images
    ] == [7, 5]
    with pytest.raises(PageSelectionError):
        renderer().render(pdf, "application/pdf", "a.pdf", [1, 2, 3, 4, 5, 6])
    with pytest.raises(PageSelectionError):
        renderer().render(pdf, "application/pdf", "a.pdf", [8])


def test_media_type_falls_back_to_file_name() -> None:
    png = encoded(Image.new("RGB", (10, 10), "white"), "PNG")

    rendered = renderer().render(png, "application/octet-stream", "photo.png", None)

    assert rendered.images[0].media_type == "image/png"


def test_docx_is_not_viewable() -> None:
    with pytest.raises(UnviewableFormatError, match="file_read"):
        renderer().render(
            b"PK\x03\x04",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "contract.docx",
            None,
        )
