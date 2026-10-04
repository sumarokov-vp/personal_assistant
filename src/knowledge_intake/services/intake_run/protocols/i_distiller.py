from typing import Protocol

from src.knowledge_intake.models.accepted_letter import AcceptedLetter
from src.knowledge_intake.services.entities.distill_outcome import DistillOutcome


class IDistiller(Protocol):
    def distill(self, letter: AcceptedLetter) -> DistillOutcome: ...
