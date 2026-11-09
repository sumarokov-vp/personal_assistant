from typing import Protocol


class IRecordingTranscriber(Protocol):
    def transcribe(
        self,
        *,
        file_id: str,
        file_name: str,
        size_bytes: int,
        chat_id: int,
        card_message_id: int,
    ) -> None: ...
