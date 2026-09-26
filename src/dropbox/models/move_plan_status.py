from enum import StrEnum


class MovePlanStatus(StrEnum):
    PROPOSED = "proposed"
    EXECUTED = "executed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"
