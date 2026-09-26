from typing import Protocol

from workers.memory_fill.protocols.i_fill_answer import IFillAnswer


class IFillConversation(Protocol):
    def process_message(self, thread_id: str, user_message: str) -> IFillAnswer: ...
