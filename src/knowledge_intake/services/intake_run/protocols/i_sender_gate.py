from typing import Protocol

from src.knowledge_intake.models.raw_letter import RawLetter
from src.knowledge_intake.services.entities.gate_verdict import GateVerdict


class ISenderGate(Protocol):
    def admit(self, letter: RawLetter) -> GateVerdict: ...
