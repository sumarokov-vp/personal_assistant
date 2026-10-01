from src.scheduler.errors.scheduler_service_error import SchedulerServiceError


class ScheduleInPastError(SchedulerServiceError):
    def __init__(self) -> None:
        super().__init__(
            "Момент at уже прошёл — расписание не заведено. Проверь дату по сегодняшней "
            "и поставь ближайший такой день в будущем."
        )
