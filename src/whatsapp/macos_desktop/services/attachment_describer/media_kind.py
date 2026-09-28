from pydantic import BaseModel, ConfigDict


class MediaKind(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    suffix: str
    media_type: str


DOCUMENT_MESSAGE_TYPE = 8
FALLBACK_KIND = MediaKind(
    label="file", suffix="", media_type="application/octet-stream"
)
KIND_BY_MESSAGE_TYPE: dict[int, MediaKind] = {
    1: MediaKind(label="image", suffix=".jpg", media_type="image/jpeg"),
    2: MediaKind(label="video", suffix=".mp4", media_type="video/mp4"),
    3: MediaKind(label="audio", suffix=".opus", media_type="audio/ogg"),
    DOCUMENT_MESSAGE_TYPE: MediaKind(
        label="document", suffix="", media_type="application/octet-stream"
    ),
    11: MediaKind(label="gif", suffix=".mp4", media_type="video/mp4"),
    15: MediaKind(label="sticker", suffix=".webp", media_type="image/webp"),
}
