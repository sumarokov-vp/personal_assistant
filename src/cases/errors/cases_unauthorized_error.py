from src.cases.errors.cases_service_error import CasesServiceError


class CasesUnauthorizedError(CasesServiceError):
    def __init__(self) -> None:
        super().__init__(
            "Сервис дел не принял ключ ассистента (CASES_API_KEY) — скажи владельцу."
        )
