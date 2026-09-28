from typing import Protocol


class IOwnerDocumentSender(Protocol):
    def send_document(self, chat_id: int, document: bytes, filename: str) -> object: ...
