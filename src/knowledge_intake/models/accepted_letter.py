from dataclasses import dataclass, field

from src.knowledge_intake.models.admitted_sender import AdmittedSender
from src.knowledge_intake.models.letter_attachment import LetterAttachment


@dataclass(frozen=True)
class AcceptedLetter:
    uid: str
    sender: AdmittedSender
    subject: str
    message_id: str
    body: str
    attachments: list[LetterAttachment] = field(default_factory=list)
