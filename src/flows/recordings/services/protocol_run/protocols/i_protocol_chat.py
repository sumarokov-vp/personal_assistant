from typing import Protocol


class IProtocolChat(Protocol):
    def send_html(self, chat_id: int, text: str) -> int: ...

    def send_pdf(
        self, chat_id: int, file_name: str, pdf: bytes, caption: str
    ) -> int: ...
