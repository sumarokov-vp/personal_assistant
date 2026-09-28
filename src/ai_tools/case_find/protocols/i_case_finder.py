from typing import Protocol

from src.cases.models.case import Case


class ICaseFinder(Protocol):
    def find_cases(self, query: str | None, status: str, limit: int) -> list[Case]: ...
