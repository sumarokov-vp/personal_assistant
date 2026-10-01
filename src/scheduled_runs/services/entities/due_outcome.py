from enum import StrEnum


class DueOutcome(StrEnum):
    DELIVERED = "delivered"
    ALREADY_DELIVERED = "already_delivered"
    REJECTED = "rejected"
