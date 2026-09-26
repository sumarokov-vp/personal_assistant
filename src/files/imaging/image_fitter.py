import io
import math

from PIL import Image, ImageOps

from src.files.imaging.image_media_type import IMAGE_MEDIA_TYPES, ImageMediaType
from src.files.imaging.rendered_image import RenderedImage

LONG_SIDE_PIXELS = 1568
JPEG_QUALITIES = (85, 70, 55, 40)
SHRINK_FACTOR = 0.75
MIN_LONG_SIDE_PIXELS = 64


# Лимит Claude на картинку считается по base64-представлению, а не по сырым байтам
def _base64_size(raw_size: int) -> int:
    return 4 * math.ceil(raw_size / 3)


class ImageFitter:
    def __init__(self, max_image_bytes: int) -> None:
        self._max_image_bytes = max_image_bytes

    def fit(self, content: bytes, media_type: str) -> RenderedImage:
        if media_type in IMAGE_MEDIA_TYPES and self._fits(content):
            return RenderedImage(
                media_type=_as_image_media_type(media_type), data=content, reduced=False
            )
        return RenderedImage(
            media_type="image/jpeg", data=self._reduce(content), reduced=True
        )

    def _fits(self, content: bytes) -> bool:
        return _base64_size(len(content)) <= self._max_image_bytes

    def _reduce(self, content: bytes) -> bytes:
        with Image.open(io.BytesIO(content)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
        long_side = LONG_SIDE_PIXELS
        while True:
            resized = image.copy()
            resized.thumbnail((long_side, long_side), Image.Resampling.LANCZOS)
            for quality in JPEG_QUALITIES:
                encoded = _jpeg(resized, quality)
                if self._fits(encoded) or long_side <= MIN_LONG_SIDE_PIXELS:
                    return encoded
            long_side = max(MIN_LONG_SIDE_PIXELS, int(long_side * SHRINK_FACTOR))


def _jpeg(image: Image.Image, quality: int) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def _as_image_media_type(media_type: str) -> ImageMediaType:
    return next(known for known in IMAGE_MEDIA_TYPES if known == media_type)
