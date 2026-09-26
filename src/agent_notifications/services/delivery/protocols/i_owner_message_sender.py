from typing import Protocol

from bot_framework import ParseMode


class IOwnerMessageSender(Protocol):
    def send(self, chat_id: int, text: str, parse_mode: ParseMode) -> object: ...
