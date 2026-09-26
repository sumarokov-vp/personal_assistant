from enum import StrEnum


class CommitmentStatus(StrEnum):
    OPEN = "открыто"
    DONE = "выполнено"
    CANCELLED = "отменено"
