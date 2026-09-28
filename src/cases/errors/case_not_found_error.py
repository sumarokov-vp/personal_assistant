from src.cases.errors.cases_service_error import CasesServiceError


class CaseNotFoundError(CasesServiceError):
    def __init__(self, case_id: str) -> None:
        super().__init__(f"Кейс не найден: {case_id}. Найди его через case_find.")
        self.case_id = case_id
