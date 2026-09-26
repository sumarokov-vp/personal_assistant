from typing import Protocol

from src.memory.models import Commitment
from src.memory.repos import UpsertOutcome


class ICommitmentStore(Protocol):
    @property
    def path(self) -> str: ...

    def find(self, what: str, parties: str) -> Commitment | None: ...

    def upsert(self, commitment: Commitment) -> UpsertOutcome: ...
