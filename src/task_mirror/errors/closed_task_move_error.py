from src.task_manager.errors.task_manager_error import TaskManagerError


class ClosedTaskMoveError(TaskManagerError):
    def __init__(self, task_id: str, status: str) -> None:
        super().__init__(f"Задача {task_id} закрыта ({status}): переносить нечего")
        self.task_id = task_id
