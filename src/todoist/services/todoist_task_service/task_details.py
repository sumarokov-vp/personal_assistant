from pydantic import BaseModel

from src.todoist.models.todoist_comment import TodoistComment
from src.todoist.services.todoist_task_service.task_card import TaskCard


class TaskDetails(BaseModel):
    task: TaskCard
    subtasks: list[TaskCard]
    comments: list[TodoistComment]
