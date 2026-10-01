from src.scheduler.errors.scheduler_service_error import SchedulerServiceError


class SchedulerUnauthorizedError(SchedulerServiceError):
    def __init__(self) -> None:
        super().__init__(
            "Сервис расписаний не принял ключ ассистента (SCHEDULER_API_KEY) — скажи "
            "владельцу."
        )
