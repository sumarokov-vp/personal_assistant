from typing import Protocol


class IDismissedCardUpdater(Protocol):
    def show_dismissed(
        self, chat_id: int, message_id: int, file_name: str, size_bytes: int
    ) -> None: ...
