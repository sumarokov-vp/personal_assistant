from typing import Protocol

from src.cases.models.case_feed import CaseFeed


class ICaseFeedSource(Protocol):
    def read_case(self, case_id: str, events_limit: int) -> CaseFeed: ...
