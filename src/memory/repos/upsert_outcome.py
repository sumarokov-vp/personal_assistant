from enum import StrEnum


class UpsertOutcome(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
