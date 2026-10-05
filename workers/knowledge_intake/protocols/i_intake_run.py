from typing import Protocol

from src.knowledge_intake import IntakeReport


class IIntakeRun(Protocol):
    def execute(self) -> IntakeReport: ...
