from enum import StrEnum


class CheckupActionOutcome(StrEnum):
    CREATED = "created"
    SKIPPED = "skipped"
    ALREADY_DONE = "already_done"
