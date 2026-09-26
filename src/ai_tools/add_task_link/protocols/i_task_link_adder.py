from typing import Protocol

from src.todoist.models.todoist_comment import TodoistComment


class ITaskLinkAdder(Protocol):
    def add_link(self, task_id: str, link: str) -> TodoistComment: ...
