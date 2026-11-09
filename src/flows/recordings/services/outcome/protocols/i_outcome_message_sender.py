from typing import Protocol


class IOutcomeMessageSender(Protocol):
    def send(self, chat_id: int, text: str) -> object: ...
