from typing import Protocol

from ai_framework.entities.message import Message


class IChatHistory(Protocol):
    def get_messages(self, thread_id: str) -> list[Message]: ...
