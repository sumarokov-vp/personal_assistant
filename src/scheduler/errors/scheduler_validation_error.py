from src.scheduler.errors.scheduler_service_error import SchedulerServiceError


class SchedulerValidationError(SchedulerServiceError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Сервис расписаний отклонил запрос: {detail[:500]}")
