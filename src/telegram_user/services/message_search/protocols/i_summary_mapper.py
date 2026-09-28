from typing import Protocol

from telethon.tl.custom.message import Message

from src.conversations.models.message_summary import MessageSummary
from src.telegram_user.models.telegram_chat import TelegramChat


class ISummaryMapper(Protocol):
    def to_summary(self, chat: TelegramChat, message: Message) -> MessageSummary: ...

    def sender(self, chat: TelegramChat, message: Message) -> str: ...
