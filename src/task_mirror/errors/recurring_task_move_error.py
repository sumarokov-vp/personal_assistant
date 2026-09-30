from src.task_manager.errors.task_manager_error import TaskManagerError


class RecurringTaskMoveError(TaskManagerError):
    def __init__(self, task_id: str, manager: str) -> None:
        super().__init__(
            f"Задача {task_id} в {manager} повторяющаяся: перенос сломает повтор. "
            f"Перенести вхождение владелец может сам в {manager}"
        )
        self.task_id = task_id
