from src.cases.errors.cases_service_error import CasesServiceError


class CasesServiceFailureError(CasesServiceError):
    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"Сервис кейсов ответил ошибкой {status_code}: {body[:200]}")
        self.status_code = status_code
