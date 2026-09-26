from typing import Protocol

from src.todoist.services.todoist_task_service.task_card import TaskCard


class IAssistantTaskCreator(Protocol):
    def create_assistant_task(
        self, content: str, due: str, description: str | None = None
    ) -> TaskCard: ...
