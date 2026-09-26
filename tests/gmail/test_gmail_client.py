import inspect
import json
from typing import Any

import httpx
import pytest

from src.gmail.errors.gmail_attachment_not_found_error import (
    GmailAttachmentNotFoundError,
)
from src.gmail.errors.gmail_attachment_too_large_error import (
    GmailAttachmentTooLargeError,
)
from src.gmail.models.mail_attachment import MailAttachment
from src.gmail.repos.gmail_client import GmailClient
from src.gmail.services.gmail_message_parser.gmail_message_parser import (
    GmailMessageParser,
)
from src.gmail.services.gmail_message_parser.html_to_text_converter import (
    HtmlToTextConverter,
)
from src.gmail.services.reply_mime_composer.reply_mime_composer import (
    ReplyMimeComposer,
)
from tests.gmail.fixtures import (
    JPEG_BYTES,
    PDF_BYTES,
    encode_bytes,
    html_only_message,
    multipart_message,
)

FORBIDDEN_VERBS = (
    "send",
    "trash",
    "delete",
    "modify",
    "label",
    "import",
    "insert",
    "batch",
    "untrash",
    "spam",
)


class StaticToken:
    def access_token(self) -> str:
        return "access-token"


def gmail_api(
    routes: dict[str, dict[str, Any]], requests: list[httpx.Request]
) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=json.dumps(routes[request.url.path]))

    return httpx.MockTransport(handle)


def make_client(
    routes: dict[str, dict[str, Any]],
    requests: list[httpx.Request],
    attachment_limit_bytes: int = 50 * 1024 * 1024,
) -> GmailClient:
    return GmailClient(
        http=httpx.Client(transport=gmail_api(routes, requests)),
        token_provider=StaticToken(),
        parser=GmailMessageParser(HtmlToTextConverter()),
        composer=ReplyMimeComposer(),
        attachment_limit_bytes=attachment_limit_bytes,
    )


BASE = "/gmail/v1/users/me/messages"


def test_search_lists_and_fetches_metadata() -> None:
    requests: list[httpx.Request] = []
    routes = {
        BASE: {
            "messages": [{"id": "18c1a", "threadId": "18c00"}],
            "resultSizeEstimate": 1,
        },
        f"{BASE}/18c1a": multipart_message(),
    }

    found = make_client(routes, requests).search_messages(
        "from:bank@example.com newer_than:30d", 5
    )

    assert len(found) == 1
    assert found[0].id == "18c1a"
    assert found[0].thread_id == "18c00"
    assert found[0].sender == "Банк <bank@example.com>"
    assert found[0].subject == "Выписка"
    assert found[0].date == "Sat, 26 Sep 2026 10:00:00 +0500"
    assert found[0].snippet == 'Привет, это "тест"'
    assert requests[0].url.params["q"] == "from:bank@example.com newer_than:30d"
    assert requests[0].url.params["maxResults"] == "5"
    assert requests[1].url.params["format"] == "metadata"
    assert all(request.method == "GET" for request in requests)
    assert all(
        request.headers["Authorization"] == "Bearer access-token"
        for request in requests
    )


def test_search_with_no_results() -> None:
    assert (
        make_client({BASE: {"resultSizeEstimate": 0}}, []).search_messages(
            "from:nobody", 10
        )
        == []
    )


def test_multipart_prefers_plain_text_and_lists_attachments() -> None:
    message = make_client({f"{BASE}/18c1a": multipart_message()}, []).get_message(
        "18c1a"
    )

    assert message.body == "Выписка за сентябрь во вложении."
    assert message.attachments == [
        MailAttachment(
            attachment_id="1",
            filename="statement.pdf",
            media_type="application/pdf",
            size=len(PDF_BYTES),
        ),
        MailAttachment(
            attachment_id="2",
            filename="receipt.jpg",
            media_type="image/jpeg",
            size=len(JPEG_BYTES),
        ),
    ]
    assert message.recipients == "me@example.com"


def test_html_only_message_is_converted_to_text() -> None:
    message = make_client({f"{BASE}/18c2b": html_only_message()}, []).get_message(
        "18c2b"
    )

    assert (
        message.body == "Здравствуйте, Владимир!\n\nСчёт № 42 & акт\n\nпервое\n\nвторое"
    )
    assert "alert" not in message.body
    assert "color" not in message.body
    assert message.attachments == []


def test_get_attachment_downloads_by_gmail_attachment_id() -> None:
    requests: list[httpx.Request] = []
    routes = {
        f"{BASE}/18c1a": multipart_message(),
        f"{BASE}/18c1a/attachments/ANGjdJ-pdf": {
            "size": len(PDF_BYTES),
            "data": encode_bytes(PDF_BYTES),
        },
    }

    content = make_client(routes, requests).get_attachment("18c1a", "1")

    assert content == PDF_BYTES
    assert [request.url.path for request in requests] == [
        f"{BASE}/18c1a",
        f"{BASE}/18c1a/attachments/ANGjdJ-pdf",
    ]
    assert all(request.method == "GET" for request in requests)


def test_get_attachment_returns_inline_body_data_without_extra_request() -> None:
    requests: list[httpx.Request] = []

    content = make_client(
        {f"{BASE}/18c1a": multipart_message()}, requests
    ).get_attachment("18c1a", "2")

    assert content == JPEG_BYTES
    assert [request.url.path for request in requests] == [f"{BASE}/18c1a"]


def test_get_attachment_refuses_part_over_limit_before_download() -> None:
    requests: list[httpx.Request] = []
    client = make_client(
        {f"{BASE}/18c1a": multipart_message()}, requests, attachment_limit_bytes=512
    )

    with pytest.raises(GmailAttachmentTooLargeError, match="statement.pdf"):
        client.get_attachment("18c1a", "1")

    assert [request.url.path for request in requests] == [f"{BASE}/18c1a"]


def test_get_attachment_of_unknown_part_is_named_error() -> None:
    client = make_client({f"{BASE}/18c1a": multipart_message()}, [])

    with pytest.raises(GmailAttachmentNotFoundError):
        client.get_attachment("18c1a", "0")


def test_client_has_no_methods_that_change_mail() -> None:
    public_methods = [
        name
        for name, _ in inspect.getmembers(GmailClient, inspect.isfunction)
        if not name.startswith("_")
    ]

    assert public_methods
    assert [
        name
        for name in public_methods
        if any(verb in name.lower() for verb in FORBIDDEN_VERBS)
    ] == []
