from enum import StrEnum


class ReceiveOutcome(StrEnum):
    RECORDED = "recorded"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"
