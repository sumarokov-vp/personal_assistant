from typing import Protocol

from src.knowledge_intake.models.accepted_letter import AcceptedLetter
from src.knowledge_intake.models.knowledge_entry import KnowledgeEntry
from src.knowledge_intake.services.entities.push_outcome import PushOutcome


class IPublisher(Protocol):
    def prepare(self) -> None: ...

    def publish(self, entry: KnowledgeEntry, letter: AcceptedLetter) -> None: ...

    def finish(self) -> PushOutcome: ...
