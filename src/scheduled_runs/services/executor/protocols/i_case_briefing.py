from typing import Protocol

from src.scheduled_runs.services.executor.case_brief import CaseBrief


class ICaseBriefing(Protocol):
    def brief(self, case_id: str) -> CaseBrief: ...
