from collections.abc import AsyncIterator
from datetime import datetime
from typing import Protocol

from telethon.tl.custom.message import Message

from src.telegram_user.models.telegram_chat import TelegramChat


class IChatHistory(Protocol):
    async def chat(self, conversation_id: str) -> TelegramChat: ...

    def history(
        self,
        chat: TelegramChat,
        search: str | None,
        until: datetime | None,
        limit: int,
    ) -> AsyncIterator[Message]: ...
