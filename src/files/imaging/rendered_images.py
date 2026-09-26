from pydantic import BaseModel, ConfigDict

from src.files.imaging.rendered_image import RenderedImage


class RenderedImages(BaseModel):
    model_config = ConfigDict(frozen=True)

    images: list[RenderedImage]
    page_count: int | None = None
