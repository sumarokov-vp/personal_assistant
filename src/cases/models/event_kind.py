from typing import Literal

EventKind = Literal[
    "note",
    "message",
    "file",
    "link",
    "task",
    "task_updated",
    "task_done",
    "task_cancelled",
    "task_reopened",
]
