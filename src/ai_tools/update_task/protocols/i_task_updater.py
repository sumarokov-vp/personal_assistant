from typing import Protocol

from src.todoist.services.todoist_task_service.task_card import TaskCard


class ITaskUpdater(Protocol):
    def update_task(
        self,
        task_id: str,
        due: str | None = None,
        deadline: str | None = None,
        clear_deadline: bool = False,
        labels: list[str] | None = None,
    ) -> TaskCard: ...
