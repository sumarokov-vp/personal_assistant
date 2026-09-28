from typing import Protocol

from src.conversations.models.source_freshness import SourceFreshness


class ISourceFreshness(Protocol):
    def freshness(self) -> SourceFreshness: ...
