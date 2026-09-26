from typing import Protocol

from src.files.imaging.rendered_image import RenderedImage


class IImageFitter(Protocol):
    def fit(self, content: bytes, media_type: str) -> RenderedImage: ...
