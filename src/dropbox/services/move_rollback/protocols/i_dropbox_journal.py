from typing import Protocol
from uuid import UUID

from src.dropbox.models.journal_entry import JournalEntry


class IDropboxJournal(Protocol):
    def append(self, entry: JournalEntry) -> None: ...

    def plan_entries(self, plan_id: UUID) -> list[JournalEntry]: ...
