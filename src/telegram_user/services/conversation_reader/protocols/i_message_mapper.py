from typing import Protocol

from telethon.tl.custom.message import Message

from src.conversations.models.conversation_message import ConversationMessage
from src.telegram_user.models.telegram_chat import TelegramChat


class IMessageMapper(Protocol):
    def to_message(
        self, chat: TelegramChat, message: Message
    ) -> ConversationMessage: ...
