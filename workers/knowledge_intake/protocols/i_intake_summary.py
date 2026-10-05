from typing import Protocol

from src.knowledge_intake import IntakeReport


class IIntakeSummary(Protocol):
    def render(self, report: IntakeReport) -> str | None: ...
