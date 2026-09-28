from src.cases.errors.cases_service_error import CasesServiceError


class TaskNotFoundError(CasesServiceError):
    def __init__(self, task_id: str) -> None:
        super().__init__(f"Задача не найдена: {task_id}.")
        self.task_id = task_id
