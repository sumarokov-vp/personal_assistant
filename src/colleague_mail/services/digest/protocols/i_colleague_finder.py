from typing import Protocol

from src.colleague_mail.models.colleague import Colleague


class IColleagueFinder(Protocol):
    def find(self, key: str) -> Colleague | None: ...
