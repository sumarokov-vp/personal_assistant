import hashlib

from pydantic import BaseModel, ConfigDict

from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow
from src.whatsapp.macos_desktop.services.entities.media_kind import media_kind
from src.whatsapp.macos_desktop.services.remote_media.cdn_link import (
    CdnLink,
    parse_cdn_link,
)
from src.whatsapp.macos_desktop.services.remote_media.media_key import (
    extract_media_key,
)

CACHE_KEY_DIGEST_CHARS = 16


class RemoteMediaSource(BaseModel):
    model_config = ConfigDict(frozen=True)

    link: CdnLink
    media_key: bytes
    key_info: bytes
    size: int
    cache_key: str


def remote_media_source(row: WhatsAppMessageRow) -> RemoteMediaSource | None:
    link = parse_cdn_link(row.media_url)
    media_key = extract_media_key(row.media_key)
    key_info = media_kind(row.message_type).cdn_key_info
    if (
        link is None
        or media_key is None
        or key_info is None
        or row.media_pk is None
        or not row.media_size
    ):
        return None
    digest = hashlib.sha256(media_key).hexdigest()[:CACHE_KEY_DIGEST_CHARS]
    return RemoteMediaSource(
        link=link,
        media_key=media_key,
        key_info=key_info,
        size=row.media_size,
        cache_key=f"{row.media_pk}-{digest}",
    )
