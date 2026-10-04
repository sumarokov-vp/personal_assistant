from dataclasses import dataclass, field


@dataclass(frozen=True)
class KnowledgeEntry:
    plugin: str
    topic: str
    when_to_apply: str
    essence: str
    subtleties: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    topic_file: str | None = None
