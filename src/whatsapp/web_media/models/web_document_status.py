from enum import StrEnum


class WebDocumentStatus(StrEnum):
    FETCHED = "fetched"
    REFUSED = "refused"
    UNREACHABLE = "unreachable"
