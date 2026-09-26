from typing import Protocol

from workers.memory_fill.page_changes import PageChanges
from workers.memory_fill.page_snapshot import PageSnapshot


class IWatchedPage(Protocol):
    def snapshot(self) -> PageSnapshot: ...

    def changes_since(self, before: PageSnapshot) -> PageChanges: ...
