from src.cases.errors.cases_service_error import CasesServiceError


class CasesValidationError(CasesServiceError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Сервис дел отклонил запрос: {detail[:500]}")
