from typing import Protocol

from telethon.tl.custom.message import Message

from src.telegram_user.models.telegram_chat import TelegramChat


class IChatMessages(Protocol):
    async def find_chat(self, conversation_id: str) -> TelegramChat | None: ...

    async def message(self, chat: TelegramChat, number: int) -> Message | None: ...
