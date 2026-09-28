from src.cases.errors.cases_service_error import CasesServiceError


class CasesServiceUnavailableError(CasesServiceError):
    def __init__(self, reason: str) -> None:
        super().__init__(
            f"Сервис дел недоступен ({reason}). Дело не прочитано и не изменено — "
            "скажи владельцу и попробуй позже."
        )
