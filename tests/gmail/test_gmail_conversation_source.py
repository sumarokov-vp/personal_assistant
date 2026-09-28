from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from src.conversations.errors.attachment_not_found_error import (
    AttachmentNotFoundError,
)
from src.conversations.errors.conversation_not_found_error import (
    ConversationNotFoundError,
)
from src.conversations.errors.message_not_found_error import MessageNotFoundError
from src.conversations.models.conversation_window import ConversationWindow
from src.conversations.models.message_query import MessageQuery
from src.gmail.repos.gmail_client import GmailClient
from src.gmail.services.conversation_source.gmail_conversation_source import (
    GmailConversationSource,
)
from src.gmail.services.conversation_source.gmail_search_query import (
    GmailSearchQuery,
)
from src.gmail.services.gmail_message_parser.gmail_message_parser import (
    GmailMessageParser,
)
from src.gmail.services.gmail_message_parser.html_to_text_converter import (
    HtmlToTextConverter,
)
from src.gmail.services.reply_mime_composer.reply_mime_composer import (
    ReplyMimeComposer,
)
from tests.gmail.fixtures import JPEG_BYTES, multipart_message
from tests.gmail.test_gmail_client import BASE, StaticToken, make_client

THREADS = "/gmail/v1/users/me/threads"
SEPTEMBER_26 = 1790402400000


def thread_message(message_id: str, day: int, *labels: str) -> dict[str, Any]:
    message = multipart_message()
    message["id"] = message_id
    message["internalDate"] = str(SEPTEMBER_26 + (day - 26) * 86_400_000)
    message["labelIds"] = list(labels)
    return message


def thread() -> dict[str, Any]:
    return {
        "id": "18c00",
        "messages": [
            thread_message("m24", 24),
            thread_message("m25", 25, "SENT"),
            thread_message("m26", 26),
        ],
    }


def missing_everywhere() -> GmailClient:
    return GmailClient(
        http=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(404))
        ),
        token_provider=StaticToken(),
        parser=GmailMessageParser(HtmlToTextConverter()),
        composer=ReplyMimeComposer(),
    )


def test_query_translates_filters_into_gmail_operators() -> None:
    query = MessageQuery(
        text="subject:счёт",
        participant="Иван Петров",
        since=datetime(2026, 9, 1, tzinfo=UTC),
        until=datetime(2026, 9, 2, tzinfo=UTC),
    )

    assert GmailSearchQuery().build(query) == (
        'subject:счёт from:"Иван Петров" after:1788220800 before:1788307200'
    )


def test_read_conversation_keeps_window_tail_and_marks_earlier() -> None:
    source = GmailConversationSource(make_client({f"{THREADS}/18c00": thread()}, []))

    conversation = source.read_conversation(
        "18c00",
        ConversationWindow(since=datetime(2026, 9, 25, tzinfo=UTC), limit=1),
    )

    assert conversation.title == "Выписка"
    assert [message.message_id for message in conversation.messages] == ["m26"]
    assert conversation.has_earlier


def test_search_inside_thread_narrows_by_gmail_query() -> None:
    requests: list[httpx.Request] = []
    routes = {
        f"{THREADS}/18c00": thread(),
        BASE: {
            "messages": [
                {"id": "m25", "threadId": "18c00"},
                {"id": "x1", "threadId": "other"},
            ]
        },
    }
    source = GmailConversationSource(make_client(routes, requests))

    found = source.search(MessageQuery(text="has:attachment", conversation_id="18c00"))

    assert [summary.message_id for summary in found] == ["m25"]
    assert found[0].has_attachments
    assert requests[1].url.params["q"] == "has:attachment"


def test_owner_messages_are_marked_from_owner() -> None:
    source = GmailConversationSource(make_client({f"{THREADS}/18c00": thread()}, []))

    messages = source.read_conversation("18c00", ConversationWindow()).messages

    assert [message.from_owner for message in messages] == [False, True, False]


def test_fetch_attachment_returns_named_content() -> None:
    source = GmailConversationSource(
        make_client({f"{BASE}/18c1a": multipart_message()}, [])
    )

    attachment = source.fetch_attachment("18c1a", "2")

    assert attachment.content == JPEG_BYTES
    assert attachment.name == "receipt.jpg"
    assert attachment.media_type == "image/jpeg"


def test_unknown_attachment_is_conversation_error() -> None:
    source = GmailConversationSource(
        make_client({f"{BASE}/18c1a": multipart_message()}, [])
    )

    with pytest.raises(AttachmentNotFoundError):
        source.fetch_attachment("18c1a", "9")


def test_missing_message_and_thread_are_conversation_errors() -> None:
    source = GmailConversationSource(missing_everywhere())

    with pytest.raises(MessageNotFoundError):
        source.read_message("nope")
    with pytest.raises(ConversationNotFoundError):
        source.read_conversation("nope", ConversationWindow())
