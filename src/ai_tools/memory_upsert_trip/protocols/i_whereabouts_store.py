from datetime import date
from typing import Protocol

from src.memory.models import Whereabouts
from src.memory.repos import UpsertOutcome


class IWhereaboutsStore(Protocol):
    @property
    def path(self) -> str: ...

    def find(self, since: date, place: str) -> Whereabouts | None: ...

    def upsert(self, whereabouts: Whereabouts) -> UpsertOutcome: ...
