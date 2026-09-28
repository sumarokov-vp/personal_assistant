import asyncio
import time
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from telethon.tl.functions.account import UpdateStatusRequest

from src.conversations.errors.attachment_not_found_error import (
    AttachmentNotFoundError,
)
from src.conversations.errors.conversation_not_found_error import (
    ConversationNotFoundError,
)
from src.conversations.errors.message_not_found_error import MessageNotFoundError
from src.conversations.models.conversation_window import ConversationWindow
from src.conversations.models.message_query import MessageQuery
from src.conversations.protocols.i_conversation_directory import (
    IConversationDirectory,
)
from src.conversations.protocols.i_conversation_source import IConversationSource
from src.telegram_user.errors.telegram_flood_wait_error import TelegramFloodWaitError
from src.telegram_user.errors.telegram_search_query_error import (
    TelegramSearchQueryError,
)
from src.telegram_user.errors.telegram_session_revoked_error import (
    TelegramSessionRevokedError,
)
from src.telegram_user.services.conversation_source.telegram_conversation_source import (
    TelegramConversationSource,
)
from tests.telegram_user.fake_telethon_client import FakeTelethonClientFactory
from tests.telegram_user.telegram_world import (
    CONTRACT_BYTES,
    CONTRACT_SIZE,
    PHOTO_BYTES,
    PHOTO_LARGEST_SIZE,
    TelegramWorld,
    moment,
)

TIMEZONE = ZoneInfo("Asia/Almaty")
ANNA = "2001"
DACHA = "-3001"
SITE = "-1000000004001"
CLUB = "-1000000004002"
NEWS = "-1000000004003"
SAVED = "1000"


@pytest.fixture
def world() -> TelegramWorld:
    return TelegramWorld()


@pytest.fixture
def source(world: TelegramWorld) -> TelegramConversationSource:
    return TelegramConversationSource(FakeTelethonClientFactory(world.client), TIMEZONE)


def test_source_satisfies_conversation_protocols(
    source: TelegramConversationSource,
) -> None:
    conversation_source: IConversationSource = source
    directory: IConversationDirectory = source
    assert conversation_source is directory


def test_global_search_drops_channel_and_links_supergroups(
    source: TelegramConversationSource,
) -> None:
    found = source.search(MessageQuery(text="договор", limit=20))

    by_chat = {summary.conversation_id: summary for summary in found}
    assert NEWS not in by_chat
    assert set(by_chat) == {ANNA, SITE, CLUB, SAVED}
    assert by_chat[SITE].link == "https://t.me/c/4001/77"
    assert by_chat[SITE].message_id == f"{SITE}:77"
    assert by_chat[CLUB].link == "https://t.me/club_test/15"
    assert by_chat[ANNA].link is None
    assert by_chat[SAVED].title == "Избранное"


def test_basic_group_message_has_no_link(source: TelegramConversationSource) -> None:
    message = source.read_message(f"{DACHA}:1")

    assert message.link is None
    assert message.sender == "Борис"
    assert message.recipients == "Дача Тест"
    assert message.date == "03.09.2026 17:00"


def test_list_conversations_drops_channel(source: TelegramConversationSource) -> None:
    chats = source.list_conversations(None, 50)

    titles = {chat.title: chat for chat in chats}
    assert set(titles) == {
        "Избранное",
        "Анна Тестовая",
        "Дача Тест",
        "Стройка Тест",
        "Клуб Тест",
    }
    assert not titles["Анна Тестовая"].is_group
    assert titles["Дача Тест"].is_group
    assert titles["Стройка Тест"].is_group
    assert titles["Клуб Тест"].last_message_date == "05.09.2026 14:00"


def test_list_conversations_filters_by_title(
    source: TelegramConversationSource,
) -> None:
    chats = source.list_conversations("тест", 2)

    assert [chat.title for chat in chats] == ["Клуб Тест", "Стройка Тест"]


def test_channel_is_not_readable(source: TelegramConversationSource) -> None:
    with pytest.raises(ConversationNotFoundError):
        source.read_conversation(NEWS, ConversationWindow())
    with pytest.raises(MessageNotFoundError):
        source.read_message(f"{NEWS}:5")
    with pytest.raises(ConversationNotFoundError):
        source.search(MessageQuery(text="договор", conversation_id=NEWS))


def test_read_private_chat_window(source: TelegramConversationSource) -> None:
    conversation = source.read_conversation(ANNA, ConversationWindow(limit=2))

    assert conversation.title == "Анна Тестовая"
    assert not conversation.is_group
    assert conversation.has_earlier
    reply, contract = conversation.messages
    assert reply.message_id == f"{ANNA}:2"
    assert reply.from_owner
    assert reply.sender == "владелец"
    assert reply.recipients == "Анна Тестовая"
    assert contract.sender == "Анна Тестовая"
    assert contract.recipients == "владелец"
    assert contract.date == "01.09.2026 15:00"


def test_read_window_since_marks_earlier(source: TelegramConversationSource) -> None:
    conversation = source.read_conversation(
        ANNA, ConversationWindow(since=moment(1, 9, 1))
    )

    assert [message.text for message in conversation.messages] == [
        "Ок, жду договор",
        "Вот договор",
    ]
    assert conversation.has_earlier


def test_read_whole_chat_has_no_earlier(source: TelegramConversationSource) -> None:
    conversation = source.read_conversation(ANNA, ConversationWindow(limit=10))

    assert len(conversation.messages) == 3
    assert not conversation.has_earlier


def test_history_requests_are_bounded(
    world: TelegramWorld, source: TelegramConversationSource
) -> None:
    source.read_conversation(ANNA, ConversationWindow(limit=10))
    source.search(MessageQuery(text="договор", limit=3))
    source.search(MessageQuery(text="договор", participant="анна", limit=3))

    assert world.client.requested_limits == [11, 3, 1000]


def test_search_in_chat_by_participant(source: TelegramConversationSource) -> None:
    found = source.search(
        MessageQuery(conversation_id=SITE, participant="анна", limit=5)
    )
    assert [summary.snippet for summary in found] == ["Договор подписан"]

    assert source.search(MessageQuery(conversation_id=SITE, participant="борис")) == []


def test_search_by_participant_username_and_until(
    source: TelegramConversationSource,
) -> None:
    found = source.search(
        MessageQuery(text="договор", participant="boris_test", limit=5)
    )
    assert [summary.conversation_id for summary in found] == [CLUB]

    earlier = source.search(
        MessageQuery(text="договор", until=datetime(2026, 9, 2, tzinfo=UTC))
    )
    assert {summary.conversation_id for summary in earlier} == {ANNA}


def test_participant_only_search_reads_named_chats(
    source: TelegramConversationSource,
) -> None:
    found = source.search(MessageQuery(participant="Анна", limit=2))

    assert [summary.message_id for summary in found] == [f"{ANNA}:3", f"{ANNA}:2"]


def test_empty_global_search_is_rejected(source: TelegramConversationSource) -> None:
    with pytest.raises(TelegramSearchQueryError):
        source.search(MessageQuery())


def test_document_attachment(source: TelegramConversationSource) -> None:
    message_id = f"{ANNA}:3"

    (attachment,) = source.list_attachments(message_id)
    assert attachment.attachment_id == "501"
    assert attachment.name == "Договор.pdf"
    assert attachment.media_type == "application/pdf"
    assert attachment.size == CONTRACT_SIZE
    assert source.read_message(message_id).attachments == [attachment]

    content = source.fetch_attachment(message_id, "501")
    assert content.content == CONTRACT_BYTES
    assert content.name == "Договор.pdf"


def test_photo_attachment_uses_largest_size(
    source: TelegramConversationSource,
) -> None:
    (attachment,) = source.list_attachments(f"{DACHA}:1")

    assert attachment.size == PHOTO_LARGEST_SIZE
    assert attachment.media_type == "image/jpeg"
    assert attachment.name == "telegram_601.jpg"
    assert source.fetch_attachment(f"{DACHA}:1", "601").content == PHOTO_BYTES
    assert source.search(MessageQuery(conversation_id=DACHA))[0].has_attachments


def test_unknown_attachment_and_message(source: TelegramConversationSource) -> None:
    with pytest.raises(AttachmentNotFoundError):
        source.fetch_attachment(f"{ANNA}:3", "999")
    with pytest.raises(MessageNotFoundError):
        source.read_message(f"{ANNA}:404")
    with pytest.raises(MessageNotFoundError):
        source.read_message("3")


def test_long_flood_wait_is_reported_without_waiting(
    world: TelegramWorld, source: TelegramConversationSource
) -> None:
    world.client.flood_seconds = 120
    started = time.monotonic()

    with pytest.raises(TelegramFloodWaitError) as raised:
        source.search(MessageQuery(text="договор"))

    assert time.monotonic() - started < 1
    assert raised.value.seconds == 120
    assert "повтори через 120 с" in str(raised.value)
    assert isinstance(world.client.requests[-1], UpdateStatusRequest)


def test_connector_only_reads_and_stays_offline(
    world: TelegramWorld, source: TelegramConversationSource
) -> None:
    source.search(MessageQuery(text="договор", limit=20))
    source.search(MessageQuery(participant="Анна"))
    source.read_conversation(DACHA, ConversationWindow())
    source.read_message(f"{SITE}:77")
    source.list_attachments(f"{ANNA}:3")
    source.fetch_attachment(f"{ANNA}:3", "501")
    source.list_conversations(None, 50)

    assert world.client.unexpected_calls == []
    assert len(world.client.requests) == 7
    assert all(
        isinstance(request, UpdateStatusRequest) and request.offline
        for request in world.client.requests
    )


def test_revoked_session_is_reported(
    world: TelegramWorld, source: TelegramConversationSource
) -> None:
    world.client.authorized = False

    with pytest.raises(TelegramSessionRevokedError):
        source.list_conversations(None, 10)


def test_connects_lazily_and_reconnects_after_drop(
    world: TelegramWorld, source: TelegramConversationSource
) -> None:
    assert world.client.connects == 0

    source.list_conversations(None, 10)
    source.list_conversations(None, 10)
    assert world.client.connects == 1

    world.client.connected = False
    source.list_conversations(None, 10)
    assert world.client.connects == 2


def test_works_when_called_from_inside_event_loop(
    source: TelegramConversationSource,
) -> None:
    async def tool_call() -> int:
        return len(source.list_conversations(None, 10))

    assert asyncio.run(tool_call()) == 5
