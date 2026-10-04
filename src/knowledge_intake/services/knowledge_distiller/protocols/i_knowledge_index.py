from typing import Protocol

from src.knowledge_intake.models.index_line import IndexLine


class IKnowledgeIndex(Protocol):
    def has_plugin(self, plugin: str) -> bool: ...

    def index_text(self, plugin: str) -> str: ...

    def index_lines(self, plugin: str) -> list[IndexLine]: ...
