from typing import Protocol

from src.dropbox.models.journal_entry import JournalEntry


class IDropboxJournalWriter(Protocol):
    def append(self, entry: JournalEntry) -> None: ...
