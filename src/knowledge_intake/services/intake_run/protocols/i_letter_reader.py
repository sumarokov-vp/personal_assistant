from typing import Protocol

from src.knowledge_intake.models.accepted_letter import AcceptedLetter
from src.knowledge_intake.models.admitted_sender import AdmittedSender
from src.knowledge_intake.models.raw_letter import RawLetter


class ILetterReader(Protocol):
    def read(self, letter: RawLetter, sender: AdmittedSender) -> AcceptedLetter: ...
