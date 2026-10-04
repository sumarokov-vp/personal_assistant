from dataclasses import dataclass

from src.knowledge_intake.models.knowledge_entry import KnowledgeEntry


@dataclass(frozen=True)
class DistillOutcome:
    entry: KnowledgeEntry | None = None
    refusal: str | None = None
