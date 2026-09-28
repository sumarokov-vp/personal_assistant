from enum import StrEnum


class AttachmentAvailability(StrEnum):
    AVAILABLE = "available"
    ON_REQUEST = "on_request"
    UNAVAILABLE = "unavailable"
