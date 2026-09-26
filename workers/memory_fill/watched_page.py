from collections.abc import Callable

from workers.memory_fill.page_changes import PageChanges
from workers.memory_fill.page_snapshot import PageSnapshot
from workers.memory_fill.protocols.i_memory_page import IMemoryPage


class WatchedPage[T]:
    def __init__(
        self,
        title: str,
        page: IMemoryPage[T],
        key: Callable[[T], tuple[str, ...]],
    ) -> None:
        self._title = title
        self._page = page
        self._key = key

    def snapshot(self) -> PageSnapshot:
        return PageSnapshot(
            entries={self._key(entry): entry for entry in self._page.read().entries}
        )

    def changes_since(self, before: PageSnapshot) -> PageChanges:
        after = self.snapshot().entries
        added = sum(1 for key in after if key not in before.entries)
        updated = sum(
            1
            for key, entry in after.items()
            if key in before.entries and before.entries[key] != entry
        )
        return PageChanges(title=self._title, added=added, updated=updated)
