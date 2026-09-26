from typing import Protocol

from src.memory.models import Commitment


class ICommitmentCloser(Protocol):
    @property
    def path(self) -> str: ...

    def close(self, what: str, parties: str) -> Commitment | None: ...
