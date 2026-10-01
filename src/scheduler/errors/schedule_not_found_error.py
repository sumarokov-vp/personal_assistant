from src.scheduler.errors.scheduler_service_error import SchedulerServiceError


class ScheduleNotFoundError(SchedulerServiceError):
    def __init__(self, schedule_id: str) -> None:
        super().__init__(
            f"Расписание не найдено: {schedule_id}. Возьми id из schedule_list."
        )
        self.schedule_id = schedule_id
