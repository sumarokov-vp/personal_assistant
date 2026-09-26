from pydantic import BaseModel, ConfigDict

from src.files.imaging.image_media_type import ImageMediaType


class RenderedImage(BaseModel):
    model_config = ConfigDict(frozen=True)

    media_type: ImageMediaType
    data: bytes
    reduced: bool
    page: int | None = None
