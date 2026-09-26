from typing import Protocol

from bot_framework.core.entities.parse_mode import ParseMode


class IPlainMessageSender(Protocol):
    def send(self, chat_id: int, text: str, parse_mode: ParseMode = ...) -> object: ...
