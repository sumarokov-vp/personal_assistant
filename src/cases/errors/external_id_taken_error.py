from src.cases.errors.cases_service_error import CasesServiceError


class ExternalIdTakenError(CasesServiceError):
    def __init__(self) -> None:
        super().__init__("Внешний id уже привязан к другой задаче.")
