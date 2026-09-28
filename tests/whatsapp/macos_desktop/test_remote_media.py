from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.conversations.errors.attachment_not_downloaded_error import (
    AttachmentNotDownloadedError,
)
from src.conversations.models.attachment_availability import AttachmentAvailability
from src.whatsapp.macos_desktop.models.cdn_download import CdnDownload
from src.whatsapp.macos_desktop.services.conversation_source.whatsapp_conversation_source import (
    WhatsAppConversationSource,
)
from src.whatsapp.macos_desktop.services.entities.media_kind import IMAGE_KEYS
from src.whatsapp.macos_desktop.services.media_cipher.media_cipher import (
    WhatsAppMediaCipher,
)
from tests.whatsapp.macos_desktop.synthetic_snapshot import SyntheticSnapshot

TIMEZONE = ZoneInfo("Asia/Almaty")

VECTOR_MEDIA_KEY = bytes(range(32))
VECTOR_PLAINTEXT = b"synthetic whatsapp media vector\n"
VECTOR_ENCRYPTED = bytes.fromhex(
    "d1ebb55266ad57a8729c602652a8745cc891fbf0f0eb363366adbaada13f1124"
    "852272eecaca7d31c829486627a1e7a2eee76b85ad3ce14c3722"
)
VECTOR_KEY_BLOB = bytes((0x0A, 0x20)) + VECTOR_MEDIA_KEY + bytes((0x18, 0x01))

LIVE_EXPIRY = "f4865700"
PAST_EXPIRY = "5e0be100"
CDN_PATH = "https://mmg.whatsapp.net/v/t62.7118-24/synthetic.enc?ccb=11-4&oh=x"


def cdn_url(expiry: str) -> str:
    return f"{CDN_PATH}&oe={expiry}&_nc_sid=5e03e0"


class ScriptedCdnClient:
    def __init__(self, download: CdnDownload) -> None:
        self._download = download
        self.requests: list[tuple[str, int]] = []

    def download(self, url: str, max_bytes: int) -> CdnDownload:
        self.requests.append((url, max_bytes))
        return self._download


class Fixture:
    def __init__(self, root: Path, cdn: ScriptedCdnClient) -> None:
        s = SyntheticSnapshot(root / "whatsapp")
        chat = s.chat("Анна Тестовая", "70000000001@s.whatsapp.net")
        at = datetime(2026, 9, 20, 9, 0, tzinfo=UTC)
        self.live_media = s.media(
            len(VECTOR_PLAINTEXT), url=cdn_url(LIVE_EXPIRY), media_key=VECTOR_KEY_BLOB
        )
        self.live = s.message(chat, at, None, message_type=1, media_pk=self.live_media)
        self.expired_media = s.media(
            len(VECTOR_PLAINTEXT), url=cdn_url(PAST_EXPIRY), media_key=VECTOR_KEY_BLOB
        )
        self.expired = s.message(
            chat, at, None, message_type=1, media_pk=self.expired_media
        )
        self.foreign_media = s.media(
            len(VECTOR_PLAINTEXT),
            url="https://example.test/photo.jpg?oe=f4865700",
            media_key=VECTOR_KEY_BLOB,
        )
        self.foreign = s.message(
            chat, at, None, message_type=1, media_pk=self.foreign_media
        )
        s.mark_captured("2026-09-20T09:10:00Z")
        self.cdn = cdn
        self.source = WhatsAppConversationSource(
            s.snapshot_dir, TIMEZONE, root / "cache", cdn
        )

    def availability(
        self, message_pk: int
    ) -> tuple[AttachmentAvailability, str | None]:
        attachment = self.source.read_message(str(message_pk)).attachments[0]
        return attachment.availability, attachment.unavailable_reason


def served(content: bytes, status: int = 200) -> ScriptedCdnClient:
    return ScriptedCdnClient(
        CdnDownload(status=status, content=content, oversized=False)
    )


def test_cipher_decrypts_reference_vector():
    plaintext = WhatsAppMediaCipher().decrypt(
        VECTOR_ENCRYPTED, VECTOR_MEDIA_KEY, IMAGE_KEYS
    )

    assert plaintext == VECTOR_PLAINTEXT


def test_cipher_rejects_tampered_mac_and_wrong_media_type():
    tampered = VECTOR_ENCRYPTED[:-1] + bytes((VECTOR_ENCRYPTED[-1] ^ 1,))
    cipher = WhatsAppMediaCipher()

    assert cipher.decrypt(tampered, VECTOR_MEDIA_KEY, IMAGE_KEYS) is None
    assert (
        cipher.decrypt(VECTOR_ENCRYPTED, VECTOR_MEDIA_KEY, b"WhatsApp Video Keys")
        is None
    )


def test_live_link_is_fetched_on_request_and_then_served_from_cache(tmp_path: Path):
    fx = Fixture(tmp_path, served(VECTOR_ENCRYPTED))

    before = fx.availability(fx.live)
    first = fx.source.fetch_attachment(str(fx.live), str(fx.live_media))
    second = fx.source.fetch_attachment(str(fx.live), str(fx.live_media))

    assert before == (AttachmentAvailability.ON_REQUEST, None)
    assert first.content == second.content == VECTOR_PLAINTEXT
    assert first.media_type == "image/jpeg"
    assert len(fx.cdn.requests) == 1
    assert fx.cdn.requests[0][1] >= len(VECTOR_ENCRYPTED)
    assert fx.availability(fx.live) == (AttachmentAvailability.AVAILABLE, None)


def test_expired_link_is_unavailable_and_not_requested(tmp_path: Path):
    fx = Fixture(tmp_path, served(VECTOR_ENCRYPTED))

    assert fx.availability(fx.expired) == (
        AttachmentAvailability.UNAVAILABLE,
        "ссылка истекла",
    )
    with pytest.raises(AttachmentNotDownloadedError, match="истекла.*WhatsApp Desktop"):
        fx.source.fetch_attachment(str(fx.expired), str(fx.expired_media))
    assert fx.cdn.requests == []


def test_cdn_refusal_reads_as_expired_link(tmp_path: Path):
    fx = Fixture(tmp_path, served(b"", status=403))

    with pytest.raises(AttachmentNotDownloadedError, match="истекла.*403"):
        fx.source.fetch_attachment(str(fx.live), str(fx.live_media))
    assert fx.availability(fx.live) == (AttachmentAvailability.ON_REQUEST, None)


def test_mac_mismatch_is_named_and_nothing_is_cached(tmp_path: Path):
    fx = Fixture(tmp_path, served(bytes(len(VECTOR_ENCRYPTED))))

    with pytest.raises(AttachmentNotDownloadedError, match="MAC не сошёлся"):
        fx.source.fetch_attachment(str(fx.live), str(fx.live_media))
    assert fx.availability(fx.live) == (AttachmentAvailability.ON_REQUEST, None)


def test_link_outside_whatsapp_cdn_is_never_requested(tmp_path: Path):
    fx = Fixture(tmp_path, served(VECTOR_ENCRYPTED))

    assert fx.availability(fx.foreign)[0] is AttachmentAvailability.UNAVAILABLE
    with pytest.raises(AttachmentNotDownloadedError, match="нет ссылки"):
        fx.source.fetch_attachment(str(fx.foreign), str(fx.foreign_media))
    assert fx.cdn.requests == []
