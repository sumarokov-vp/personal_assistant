from enum import StrEnum


class MailboxFolder(StrEnum):
    PROCESSED = "Processed"
    REJECTED = "Rejected"
