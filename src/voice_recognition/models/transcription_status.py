from enum import StrEnum


class TranscriptionStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def is_finished(self) -> bool:
        return self in (TranscriptionStatus.COMPLETED, TranscriptionStatus.FAILED)
