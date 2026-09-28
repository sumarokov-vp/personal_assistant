from datetime import date
from typing import Protocol


class ITaskMirror(Protocol):
    def mirror(self, task_id: str, summary: str, due: date | None) -> None: ...
