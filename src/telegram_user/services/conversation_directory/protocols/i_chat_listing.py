from collections.abc import AsyncIterator
from typing import Protocol

from src.telegram_user.models.telegram_chat import TelegramChat


class IChatListing(Protocol):
    def chats(self) -> AsyncIterator[TelegramChat]: ...
