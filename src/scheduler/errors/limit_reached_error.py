from src.scheduler.errors.scheduler_service_error import SchedulerServiceError


class LimitReachedError(SchedulerServiceError):
    def __init__(self, limit: int) -> None:
        super().__init__(
            f"Живых расписаний уже {limit} — это предел, новое не заведено. Покажи "
            "владельцу список (schedule_list) и предложи отменить ненужные."
        )
        self.limit = limit
