from typing import Protocol


class IRecordingQuestionCard(Protocol):
    def send_question(
        self, chat_id: int, intake_id: str, file_name: str, size_bytes: int
    ) -> None: ...

    def send_too_large(
        self, chat_id: int, file_name: str, size_bytes: int, max_bytes: int
    ) -> None: ...
