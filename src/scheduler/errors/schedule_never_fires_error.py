from src.scheduler.errors.scheduler_service_error import SchedulerServiceError


class ScheduleNeverFiresError(SchedulerServiceError):
    def __init__(self) -> None:
        super().__init__(
            "По этому cron нет ни одного срабатывания (например, 31 февраля) — расписание "
            "не заведено. Исправь выражение."
        )
