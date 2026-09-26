from enum import StrEnum


class DeliveryOutcome(StrEnum):
    DELIVERED = "delivered"
    ALREADY_DELIVERED = "already_delivered"
    REJECTED = "rejected"
