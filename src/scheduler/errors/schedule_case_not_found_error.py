from src.scheduler.errors.scheduler_service_error import SchedulerServiceError


class ScheduleCaseNotFoundError(SchedulerServiceError):
    def __init__(self, case_id: str) -> None:
        super().__init__(
            f"Кейс не найден: {case_id} — расписание не заведено. Найди кейс через "
            "case_find и возьми его case_id; темы нет — case_id inbox."
        )
        self.case_id = case_id
