from typing import Protocol

from src.cases.models.case import Case


class ICaseOpener(Protocol):
    def create_case(self, title: str, summary: str | None) -> Case: ...
