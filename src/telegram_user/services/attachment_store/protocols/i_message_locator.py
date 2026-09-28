from typing import Protocol

from telethon.tl.custom.message import Message

from src.telegram_user.models.telegram_chat import TelegramChat


class IMessageLocator(Protocol):
    async def locate(self, message_id: str) -> tuple[TelegramChat, Message]: ...
