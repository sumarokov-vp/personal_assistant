from zoneinfo import ZoneInfo

import pytest
from telethon.tl.types import User

from src.conversations.errors.conversation_not_found_error import (
    ConversationNotFoundError,
)
from src.conversations.errors.message_not_found_error import MessageNotFoundError
from src.conversations.models.conversation_window import ConversationWindow
from src.conversations.models.message_query import MessageQuery
from src.telegram_user.services.conversation_source.telegram_conversation_source import (
    TelegramConversationSource,
)
from tests.telegram_user.fake_telethon_client import FakeTelethonClientFactory
from tests.telegram_user.telegram_world import CONTRACT_BYTES, TelegramWorld, moment

TIMEZONE = ZoneInfo("Asia/Almaty")
ASSISTANT_BOT = "7001"
WEATHER_BOT = "7002"
NEWS = "-1000000004003"


@pytest.fixture
def source() -> TelegramConversationSource:
    world = TelegramWorld()
    client = world.client
    assistant = User(id=7001, bot=True, first_name="Personal Assistant", access_hash=71)
    weather = User(id=7002, bot=True, first_name="Погода", access_hash=72)
    client.add_chat(assistant, moment(7, 9))
    client.add_chat(weather, moment(7, 8))
    client.add_message(
        assistant,
        1,
        moment(7, 9),
        "Договор ассистенту",
        out=True,
        media=world.anna_contract.media,
        content=CONTRACT_BYTES,
    )
    client.add_message(weather, 1, moment(7, 8), "Договор погоды", sender=weather)
    return TelegramConversationSource(
        FakeTelethonClientFactory(client), TIMEZONE, frozenset({ASSISTANT_BOT})
    )


def test_assistant_bot_chat_is_not_listed(source: TelegramConversationSource) -> None:
    listed = {chat.conversation_id for chat in source.list_conversations(None, 50)}

    assert ASSISTANT_BOT not in listed
    assert WEATHER_BOT in listed


def test_assistant_bot_chat_is_not_found_by_global_search(
    source: TelegramConversationSource,
) -> None:
    found = {
        summary.conversation_id
        for summary in source.search(MessageQuery(text="договор", limit=50))
    }

    assert ASSISTANT_BOT not in found
    assert WEATHER_BOT in found


@pytest.mark.parametrize("conversation_id", [ASSISTANT_BOT, NEWS])
def test_assistant_bot_chat_is_unreadable_like_channel(
    source: TelegramConversationSource, conversation_id: str
) -> None:
    with pytest.raises(ConversationNotFoundError):
        source.search(MessageQuery(text="договор", conversation_id=conversation_id))
    with pytest.raises(ConversationNotFoundError):
        source.read_conversation(conversation_id, ConversationWindow())


def test_assistant_bot_message_and_attachment_are_not_found(
    source: TelegramConversationSource,
) -> None:
    source.search(MessageQuery(text="договор", limit=50))
    message_id = f"{ASSISTANT_BOT}:1"

    with pytest.raises(MessageNotFoundError):
        source.read_message(message_id)
    with pytest.raises(MessageNotFoundError):
        source.list_attachments(message_id)
    with pytest.raises(MessageNotFoundError):
        source.fetch_attachment(message_id, "501")


def test_other_bot_chat_is_readable(source: TelegramConversationSource) -> None:
    conversation = source.read_conversation(WEATHER_BOT, ConversationWindow())

    assert conversation.title == "Погода"
    assert source.read_message(f"{WEATHER_BOT}:1").text == "Договор погоды"
