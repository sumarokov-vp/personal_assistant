from typing import Protocol

from src.knowledge_intake.services.entities.dkim_result import DkimResult


class IDkimCheck(Protocol):
    def check(self, raw: bytes, domain: str) -> DkimResult: ...
