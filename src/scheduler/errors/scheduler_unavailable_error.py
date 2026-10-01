from src.scheduler.errors.scheduler_service_error import SchedulerServiceError


class SchedulerUnavailableError(SchedulerServiceError):
    def __init__(self, reason: str) -> None:
        super().__init__(
            f"Сервис расписаний недоступен ({reason}). Расписание не заведено и не "
            "изменено — скажи владельцу и попробуй позже."
        )
