from typing import Protocol


class IProtocolCrashReport(Protocol):
    def send_html(self, chat_id: int, text: str) -> int: ...
