from src.scheduler.errors.scheduler_service_error import SchedulerServiceError


class CasesUnavailableError(SchedulerServiceError):
    def __init__(self) -> None:
        super().__init__(
            "Сервис расписаний не смог проверить кейс: сервис кейсов недоступен. "
            "Расписание не заведено — скажи владельцу и попробуй позже."
        )
