import time
from collections.abc import Callable

from src.conversations.errors.attachment_not_downloaded_error import (
    AttachmentNotDownloadedError,
)
from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow
from src.whatsapp.macos_desktop.services.remote_media.protocols.i_cdn_client import (
    ICdnClient,
)
from src.whatsapp.macos_desktop.services.remote_media.protocols.i_document_fallback import (
    IDocumentFallback,
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
from src.whatsapp.macos_desktop.services.remote_media.web_document_request import (
    web_document_request,
)
from src.whatsapp.web_media.models.web_document_status import WebDocumentStatus

OK = 200
EXPIRED_LINK_STATUSES = frozenset({403, 404, 410})
ENCRYPTION_OVERHEAD_BYTES = 16 + 10

NO_LINK_REASON = "у вложения нет ссылки WhatsApp для скачивания"
EXPIRED_REASON = "ссылка WhatsApp на файл истекла (живёт около 30 дней)"
OVERSIZED_REASON = "CDN WhatsApp отдал больше, чем размер файла"
MAC_REASON = "MAC не сошёлся: файл с CDN повреждён или ключ не тот"
WEB_UNREACHABLE_REASON = "запасной путь WhatsApp Web не ответил"
WEB_REFUSED_PREFIX = "через WhatsApp Web не получилось"


class WhatsAppRemoteMedia:
    def __init__(
        self,
        cache: IMediaCache,
        client: ICdnClient,
        cipher: IMediaCipher,
        clock: Callable[[], float] = time.time,
        fallback: IDocumentFallback | None = None,
    ) -> None:
        self._cache = cache
        self._client = client
        self._cipher = cipher
        self._clock = clock
        self._fallback = fallback

    def state(self, row: WhatsAppMessageRow) -> RemoteMediaState:
        source = remote_media_source(row)
        if source is None:
            return RemoteMediaState.NO_LINK
        if self._cache.find(source.cache_key) is not None:
            return RemoteMediaState.CACHED
        if source.link.expired(self._clock()) and not self._has_fallback(row):
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
        content = (
            self._from_web(row, source, name, EXPIRED_REASON, desktop_hint)
            if source.link.expired(self._clock())
            else self._download(row, source, name, desktop_hint)
        )
        self._cache.store(source.cache_key, content)
        return content

    def _has_fallback(self, row: WhatsAppMessageRow) -> bool:
        return self._fallback is not None and web_document_request(row) is not None

    def _from_web(
        self,
        row: WhatsAppMessageRow,
        source: RemoteMediaSource,
        name: str,
        cdn_reason: str,
        desktop_hint: str,
    ) -> bytes:
        request = web_document_request(row)
        if self._fallback is None or request is None:
            raise AttachmentNotDownloadedError(name, f"{cdn_reason}; {desktop_hint}")
        outcome = self._fallback.fetch_document(request)
        if outcome.status is WebDocumentStatus.UNREACHABLE:
            reason = f"{cdn_reason}; {WEB_UNREACHABLE_REASON}"
            raise AttachmentNotDownloadedError(name, f"{reason}; {desktop_hint}")
        if outcome.status is WebDocumentStatus.REFUSED:
            reason = f"{cdn_reason}; {WEB_REFUSED_PREFIX}: {outcome.reason}"
            raise AttachmentNotDownloadedError(name, f"{reason}; {desktop_hint}")
        if len(outcome.content) != source.size:
            reason = (
                f"WhatsApp Web отдал {len(outcome.content)} Б, "
                f"а размер в WhatsApp {source.size} Б"
            )
            raise AttachmentNotDownloadedError(name, f"{reason}; {desktop_hint}")
        return outcome.content

    def _download(
        self,
        row: WhatsAppMessageRow,
        source: RemoteMediaSource,
        name: str,
        desktop_hint: str,
    ) -> bytes:
        download = self._client.download(
            source.link.url, source.size + ENCRYPTION_OVERHEAD_BYTES
        )
        if download.status in EXPIRED_LINK_STATUSES:
            reason = f"ссылка WhatsApp на файл истекла (CDN ответил {download.status})"
            return self._from_web(row, source, name, reason, desktop_hint)
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
