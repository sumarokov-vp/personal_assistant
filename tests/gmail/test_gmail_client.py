import inspect
import json
from typing import Any

import httpx

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
from tests.gmail.fixtures import html_only_message, multipart_message

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
    routes: dict[str, dict[str, Any]], requests: list[httpx.Request]
) -> GmailClient:
    return GmailClient(
        http=httpx.Client(transport=gmail_api(routes, requests)),
        token_provider=StaticToken(),
        parser=GmailMessageParser(HtmlToTextConverter()),
        composer=ReplyMimeComposer(),
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


def test_multipart_prefers_plain_text_and_lists_attachment_names() -> None:
    message = make_client({f"{BASE}/18c1a": multipart_message()}, []).get_message(
        "18c1a"
    )

    assert message.body == "Выписка за сентябрь во вложении."
    assert message.attachment_names == ["statement.pdf"]
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
    assert message.attachment_names == []


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
