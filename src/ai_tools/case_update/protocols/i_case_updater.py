from typing import Protocol

from src.cases.models.case import Case
from src.cases.models.case_update import CaseUpdate


class ICaseUpdater(Protocol):
    def update_case(self, case_id: str, update: CaseUpdate) -> Case: ...
