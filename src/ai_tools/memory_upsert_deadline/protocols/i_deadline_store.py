from typing import Protocol

from src.memory.models import Deadline
from src.memory.repos import UpsertOutcome


class IDeadlineStore(Protocol):
    @property
    def path(self) -> str: ...

    def find(self, what: str, whose: str) -> Deadline | None: ...

    def upsert(self, deadline: Deadline) -> UpsertOutcome: ...
