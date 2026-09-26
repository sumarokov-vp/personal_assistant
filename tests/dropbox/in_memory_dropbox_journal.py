from uuid import UUID

from src.dropbox.models.journal_entry import JournalEntry


class InMemoryDropboxJournal:
    def __init__(self) -> None:
        self.entries: list[JournalEntry] = []

    def append(self, entry: JournalEntry) -> None:
        self.entries.append(entry)

    def plan_entries(self, plan_id: UUID) -> list[JournalEntry]:
        return [entry for entry in self.entries if entry.plan_id == plan_id]
