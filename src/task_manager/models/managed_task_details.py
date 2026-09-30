from pydantic import BaseModel

from src.task_manager.models.managed_task import ManagedTask
from src.task_manager.models.task_comment import TaskComment


class ManagedTaskDetails(BaseModel):
    task: ManagedTask
    subtasks: list[ManagedTask]
    comments: list[TaskComment]
