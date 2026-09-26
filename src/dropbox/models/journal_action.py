from enum import StrEnum


class JournalAction(StrEnum):
    ADDED = "added"
    MOVED = "moved"
    MOVE_ROLLED_BACK = "move_rolled_back"
    ROLLBACK_SKIPPED = "rollback_skipped"
