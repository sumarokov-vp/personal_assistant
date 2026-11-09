from typing import Protocol


class IRecognizingCardUpdater(Protocol):
    def show_recognizing(
        self, chat_id: int, message_id: int, file_name: str, size_bytes: int
    ) -> None: ...
