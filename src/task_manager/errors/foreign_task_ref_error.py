from src.task_manager.errors.task_manager_error import TaskManagerError


class ForeignTaskRefError(TaskManagerError):
    def __init__(self, ref: str, manager: str) -> None:
        super().__init__(f"Задача {ref} не из задачника {manager}")
        self.ref = ref
