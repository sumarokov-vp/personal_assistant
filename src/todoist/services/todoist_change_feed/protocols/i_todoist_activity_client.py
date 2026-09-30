from datetime import datetime
from typing import Protocol

from src.todoist.models.todoist_activity import TodoistActivity


class ITodoistActivityClient(Protocol):
    def list_activities(
        self, object_event_types: list[str], since: datetime
    ) -> list[TodoistActivity]: ...
