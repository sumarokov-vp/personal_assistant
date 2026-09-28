from pydantic import BaseModel, ConfigDict


class MediaKind(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    suffix: str
    media_type: str
    cdn_key_info: bytes | None


IMAGE_KEYS = b"WhatsApp Image Keys"
VIDEO_KEYS = b"WhatsApp Video Keys"
AUDIO_KEYS = b"WhatsApp Audio Keys"
DOCUMENT_KEYS = b"WhatsApp Document Keys"

DOCUMENT_MESSAGE_TYPE = 8
FALLBACK_KIND = MediaKind(
    label="file", suffix="", media_type="application/octet-stream", cdn_key_info=None
)
IMAGE_KIND = MediaKind(
    label="image", suffix=".jpg", media_type="image/jpeg", cdn_key_info=IMAGE_KEYS
)
VIDEO_KIND = MediaKind(
    label="video", suffix=".mp4", media_type="video/mp4", cdn_key_info=VIDEO_KEYS
)
KIND_BY_MESSAGE_TYPE: dict[int, MediaKind] = {
    1: IMAGE_KIND,
    2: VIDEO_KIND,
    3: MediaKind(
        label="audio", suffix=".opus", media_type="audio/ogg", cdn_key_info=AUDIO_KEYS
    ),
    DOCUMENT_MESSAGE_TYPE: MediaKind(
        label="document",
        suffix="",
        media_type="application/octet-stream",
        cdn_key_info=DOCUMENT_KEYS,
    ),
    11: MediaKind(
        label="gif", suffix=".mp4", media_type="video/mp4", cdn_key_info=VIDEO_KEYS
    ),
    15: MediaKind(
        label="sticker",
        suffix=".webp",
        media_type="image/webp",
        cdn_key_info=IMAGE_KEYS,
    ),
    42: IMAGE_KIND,
    54: VIDEO_KIND,
}


def media_kind(message_type: int | None) -> MediaKind:
    if message_type is None:
        return FALLBACK_KIND
    return KIND_BY_MESSAGE_TYPE.get(message_type, FALLBACK_KIND)
