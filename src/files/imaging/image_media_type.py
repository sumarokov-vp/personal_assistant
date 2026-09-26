from typing import Literal

ImageMediaType = Literal["image/png", "image/jpeg", "image/gif", "image/webp"]

IMAGE_MEDIA_TYPES: tuple[ImageMediaType, ...] = (
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
)
