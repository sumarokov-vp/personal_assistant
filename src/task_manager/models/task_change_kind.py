from typing import Literal

TaskChangeKind = Literal[
    "closed", "reopened", "deleted", "deadline_changed", "due_changed"
]
