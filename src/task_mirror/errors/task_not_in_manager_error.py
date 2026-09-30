from src.task_manager.errors.task_manager_error import TaskManagerError


class TaskNotInManagerError(TaskManagerError):
    def __init__(self, task_id: str, manager: str) -> None:
        super().__init__(
            f"Задача {task_id} не стоит в задачнике {manager}: дату выполнения "
            "менять негде. Срок-дедлайн меняет due"
        )
        self.task_id = task_id
