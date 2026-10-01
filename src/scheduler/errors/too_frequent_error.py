from src.scheduler.errors.scheduler_service_error import SchedulerServiceError


class TooFrequentError(SchedulerServiceError):
    def __init__(self, min_interval_minutes: int) -> None:
        super().__init__(
            f"Слишком часто: расписание не может срабатывать чаще раза в "
            f"{min_interval_minutes} мин — не заведено. Скажи владельцу и предложи "
            "интервал реже."
        )
        self.min_interval_minutes = min_interval_minutes
