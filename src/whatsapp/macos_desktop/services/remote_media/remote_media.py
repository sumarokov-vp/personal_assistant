import time
from collections.abc import Callable

from src.conversations.errors.attachment_not_downloaded_error import (
    AttachmentNotDownloadedError,
)
from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow
from src.whatsapp.macos_desktop.services.remote_media.protocols.i_cdn_client import (
    ICdnClient,
)
from src.whatsapp.macos_desktop.services.remote_media.protocols.i_media_cache import (
    IMediaCache,
)
from src.whatsapp.macos_desktop.services.remote_media.protocols.i_media_cipher import (
    IMediaCipher,
)
from src.whatsapp.macos_desktop.services.remote_media.remote_media_source import (
    RemoteMediaSource,
    remote_media_source,
)
from src.whatsapp.macos_desktop.services.remote_media.remote_media_state import (
    RemoteMediaState,
)

OK = 200
EXPIRED_LINK_STATUSES = frozenset({403, 404, 410})
ENCRYPTION_OVERHEAD_BYTES = 16 + 10

NO_LINK_REASON = "у вложения нет ссылки WhatsApp для скачивания"
EXPIRED_REASON = "ссылка WhatsApp на файл истекла (живёт около 30 дней)"
OVERSIZED_REASON = "CDN WhatsApp отдал больше, чем размер файла"
MAC_REASON = "MAC не сошёлся: файл с CDN повреждён или ключ не тот"


class WhatsAppRemoteMedia:
    def __init__(
        self,
        cache: IMediaCache,
        client: ICdnClient,
        cipher: IMediaCipher,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._cache = cache
        self._client = client
        self._cipher = cipher
        self._clock = clock

    def state(self, row: WhatsAppMessageRow) -> RemoteMediaState:
        source = remote_media_source(row)
        if source is None:
            return RemoteMediaState.NO_LINK
        if self._cache.find(source.cache_key) is not None:
            return RemoteMediaState.CACHED
        if source.link.expired(self._clock()):
            return RemoteMediaState.EXPIRED
        return RemoteMediaState.ON_REQUEST

    def fetch(self, row: WhatsAppMessageRow, name: str, desktop_hint: str) -> bytes:
        source = remote_media_source(row)
        if source is None:
            raise AttachmentNotDownloadedError(
                name, f"{NO_LINK_REASON}; {desktop_hint}"
            )
        cached = self._cache.find(source.cache_key)
        if cached is not None:
            return cached.read_bytes()
        if source.link.expired(self._clock()):
            raise AttachmentNotDownloadedError(
                name, f"{EXPIRED_REASON}; {desktop_hint}"
            )
        content = self._download(source, name, desktop_hint)
        self._cache.store(source.cache_key, content)
        return content

    def _download(
        self, source: RemoteMediaSource, name: str, desktop_hint: str
    ) -> bytes:
        download = self._client.download(
            source.link.url, source.size + ENCRYPTION_OVERHEAD_BYTES
        )
        if download.status in EXPIRED_LINK_STATUSES:
            reason = f"ссылка WhatsApp на файл истекла (CDN ответил {download.status})"
            raise AttachmentNotDownloadedError(name, f"{reason}; {desktop_hint}")
        if download.status != OK:
            reason = f"ошибка сети: CDN WhatsApp ответил {download.status}"
            raise AttachmentNotDownloadedError(name, f"{reason}; {desktop_hint}")
        if download.oversized:
            raise AttachmentNotDownloadedError(
                name, f"{OVERSIZED_REASON}; {desktop_hint}"
            )
        content = self._cipher.decrypt(
            download.content, source.media_key, source.key_info
        )
        if content is None:
            raise AttachmentNotDownloadedError(name, f"{MAC_REASON}; {desktop_hint}")
        if len(content) != source.size:
            reason = (
                f"размер после расшифровки {len(content)} Б не совпал "
                f"с размером в WhatsApp {source.size} Б"
            )
            raise AttachmentNotDownloadedError(name, f"{reason}; {desktop_hint}")
        return content
