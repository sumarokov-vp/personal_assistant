from src.scheduler.errors.scheduler_service_error import SchedulerServiceError


class SchedulerFailureError(SchedulerServiceError):
    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(
            f"Сервис расписаний ответил ошибкой {status_code}: {body[:200]}"
        )
        self.status_code = status_code
