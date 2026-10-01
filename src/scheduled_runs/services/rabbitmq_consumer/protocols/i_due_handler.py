from typing import Protocol

from src.scheduled_runs.services.entities.due_outcome import DueOutcome
from src.scheduled_runs.services.entities.incoming_due import IncomingDue


class IDueHandler(Protocol):
    def handle(self, incoming: IncomingDue) -> DueOutcome: ...
