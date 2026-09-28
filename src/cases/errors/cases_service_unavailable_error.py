from src.cases.errors.cases_service_error import CasesServiceError


class CasesServiceUnavailableError(CasesServiceError):
    def __init__(self, reason: str) -> None:
        super().__init__(
            f"Сервис кейсов недоступен ({reason}). Кейс не прочитан и не изменён — "
            "скажи владельцу и попробуй позже."
        )
