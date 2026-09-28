from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
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
from src.whatsapp.web_media.repos.whatsapp_web_client import WhatsAppWebClient
from tests.whatsapp.macos_desktop.synthetic_snapshot import SyntheticSnapshot
from workers.bot.whatsapp_tools_factory import build_whatsapp_web_client

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


WEB_URL = "http://host.docker.internal:18790"
WEB_DOCUMENT = b"%PDF-1.7 synthetic document from web"
DOCUMENT_MESSAGE_TYPE = 8


class FakeWebService:
    def __init__(self, response: httpx.Response | None) -> None:
        self._response = response
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self._response is None:
            raise httpx.ConnectError("connection refused", request=request)
        return self._response

    def client(self) -> WhatsAppWebClient:
        return WhatsAppWebClient(
            WEB_URL, "web-secret", transport=httpx.MockTransport(self.handle)
        )


class DocumentFixture:
    def __init__(
        self, root: Path, cdn: ScriptedCdnClient, web: FakeWebService | None
    ) -> None:
        s = SyntheticSnapshot(root / "whatsapp")
        chat = s.chat("Бухгалтерия Тест", "70000000003@s.whatsapp.net")
        at = datetime(2026, 9, 7, 8, 15, tzinfo=UTC)
        self.live_media = s.media(
            len(WEB_DOCUMENT),
            title="Счёт 0001.pdf",
            url=cdn_url(LIVE_EXPIRY),
            media_key=VECTOR_KEY_BLOB,
        )
        self.live = s.message(
            chat, at, None, message_type=DOCUMENT_MESSAGE_TYPE, media_pk=self.live_media
        )
        self.expired_media = s.media(
            len(WEB_DOCUMENT),
            title="Акт 0002.pdf",
            url=cdn_url(PAST_EXPIRY),
            media_key=VECTOR_KEY_BLOB,
        )
        self.expired = s.message(
            chat,
            at,
            None,
            message_type=DOCUMENT_MESSAGE_TYPE,
            media_pk=self.expired_media,
        )
        self.untitled_media = s.media(
            len(WEB_DOCUMENT), url=cdn_url(LIVE_EXPIRY), media_key=VECTOR_KEY_BLOB
        )
        self.untitled = s.message(
            chat,
            at,
            "Договор 0003",
            message_type=DOCUMENT_MESSAGE_TYPE,
            media_pk=self.untitled_media,
        )
        s.mark_captured("2026-09-20T09:10:00Z")
        self.cdn = cdn
        self.web = web
        self.source = WhatsAppConversationSource(
            s.snapshot_dir,
            TIMEZONE,
            root / "cache",
            cdn,
            document_fallback=None if web is None else web.client(),
        )

    def availability(
        self, message_pk: int
    ) -> tuple[AttachmentAvailability, str | None]:
        attachment = self.source.read_message(str(message_pk)).attachments[0]
        return attachment.availability, attachment.unavailable_reason

    def web_requests(self) -> list[httpx.Request]:
        return [] if self.web is None else self.web.requests


def web_serving(content: bytes = WEB_DOCUMENT) -> FakeWebService:
    return FakeWebService(httpx.Response(200, content=content))


def web_refusing(status: int, code: str, detail: str) -> FakeWebService:
    return FakeWebService(
        httpx.Response(status, json={"error": code, "detail": detail})
    )


def test_cdn_gone_document_comes_from_web_into_the_cache(tmp_path: Path):
    fx = DocumentFixture(tmp_path, served(b"", status=410), web_serving())

    first = fx.source.fetch_attachment(str(fx.live), str(fx.live_media))
    second = fx.source.fetch_attachment(str(fx.live), str(fx.live_media))

    assert first.content == second.content == WEB_DOCUMENT
    assert first.name == "Счёт 0001.pdf"
    assert len(fx.cdn.requests) == 1
    assert len(fx.web_requests()) == 1
    body = fx.web_requests()[0].read().decode()
    assert '"file_name":"Счёт 0001.pdf"' in body
    assert '"chat_title":"Бухгалтерия Тест"' in body
    assert fx.availability(fx.live) == (AttachmentAvailability.AVAILABLE, None)


def test_document_without_ztitle_asks_web_by_name_from_ztext(tmp_path: Path):
    fx = DocumentFixture(tmp_path, served(b"", status=410), web_serving())

    fetched = fx.source.fetch_attachment(str(fx.untitled), str(fx.untitled_media))

    assert fetched.content == WEB_DOCUMENT
    assert len(fx.web_requests()) == 1
    assert '"file_name":"Договор 0003"' in fx.web_requests()[0].read().decode()


def test_expired_link_goes_straight_to_web(tmp_path: Path):
    fx = DocumentFixture(tmp_path, served(VECTOR_ENCRYPTED), web_serving())

    before = fx.availability(fx.expired)
    fetched = fx.source.fetch_attachment(str(fx.expired), str(fx.expired_media))

    assert before == (AttachmentAvailability.ON_REQUEST, None)
    assert fetched.content == WEB_DOCUMENT
    assert fx.cdn.requests == []
    assert len(fx.web_requests()) == 1


@pytest.mark.parametrize(
    ("status", "code", "words"),
    [
        (409, "not_linked", "код перепривязки придёт в Telegram"),
        (504, "reupload_timeout", "телефон не прислал файл"),
        (404, "document_not_found", "документ не нашёлся"),
        (502, "ui_changed", "изменился интерфейс WhatsApp Web"),
    ],
)
def test_web_refusal_is_named_in_the_error(
    tmp_path: Path, status: int, code: str, words: str
):
    fx = DocumentFixture(
        tmp_path, served(b"", status=410), web_refusing(status, code, "пояснение")
    )

    with pytest.raises(AttachmentNotDownloadedError) as raised:
        fx.source.fetch_attachment(str(fx.live), str(fx.live_media))

    message = str(raised.value)
    assert "CDN ответил 410" in message
    assert words in message
    assert "пояснение" in message
    assert "WhatsApp Desktop" in message


def test_unreachable_web_keeps_cdn_reason_and_says_web_did_not_answer(
    tmp_path: Path,
):
    fx = DocumentFixture(tmp_path, served(b"", status=410), FakeWebService(None))

    with pytest.raises(
        AttachmentNotDownloadedError,
        match="истекла \\(CDN ответил 410\\); запасной путь WhatsApp Web не ответил",
    ):
        fx.source.fetch_attachment(str(fx.live), str(fx.live_media))


def test_web_file_of_other_size_is_rejected_and_not_cached(tmp_path: Path):
    fx = DocumentFixture(tmp_path, served(b"", status=410), web_serving(b"short"))

    with pytest.raises(AttachmentNotDownloadedError, match="размер в WhatsApp"):
        fx.source.fetch_attachment(str(fx.live), str(fx.live_media))
    assert fx.availability(fx.live) == (AttachmentAvailability.ON_REQUEST, None)


def test_without_web_url_web_is_never_asked(tmp_path: Path):
    fx = DocumentFixture(tmp_path, served(b"", status=410), None)

    assert build_whatsapp_web_client(None, "web-secret") is None
    assert fx.availability(fx.expired) == (
        AttachmentAvailability.UNAVAILABLE,
        "ссылка истекла",
    )
    with pytest.raises(AttachmentNotDownloadedError, match="истекла.*WhatsApp Desktop"):
        fx.source.fetch_attachment(str(fx.expired), str(fx.expired_media))
    with pytest.raises(AttachmentNotDownloadedError, match="CDN ответил 410"):
        fx.source.fetch_attachment(str(fx.live), str(fx.live_media))


def test_photo_gone_from_cdn_is_not_asked_from_web(tmp_path: Path):
    web = web_serving()
    fx = Fixture(tmp_path, served(b"", status=410))
    fx.source = WhatsAppConversationSource(
        tmp_path / "whatsapp",
        TIMEZONE,
        tmp_path / "cache",
        fx.cdn,
        document_fallback=web.client(),
    )

    assert fx.availability(fx.expired)[0] is AttachmentAvailability.UNAVAILABLE
    with pytest.raises(AttachmentNotDownloadedError, match="CDN ответил 410"):
        fx.source.fetch_attachment(str(fx.live), str(fx.live_media))
    assert web.requests == []
