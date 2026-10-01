from src.scheduler.errors.scheduler_service_error import SchedulerServiceError


class ScheduleFinishedError(SchedulerServiceError):
    def __init__(self, schedule_id: str) -> None:
        super().__init__(f"Расписание {schedule_id} уже выполнено — отменять нечего.")
        self.schedule_id = schedule_id
