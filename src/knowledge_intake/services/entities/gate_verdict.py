from dataclasses import dataclass

from src.knowledge_intake.models.admitted_sender import AdmittedSender


@dataclass(frozen=True)
class GateVerdict:
    address: str
    sender: AdmittedSender | None = None
    reason: str | None = None
