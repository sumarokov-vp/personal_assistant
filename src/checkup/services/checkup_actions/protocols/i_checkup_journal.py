from typing import Protocol

from src.checkup.models.checkup_journal_entry import CheckupJournalEntry


class ICheckupJournal(Protocol):
    def find(self, key_text: str) -> CheckupJournalEntry | None: ...

    def record(self, entry: CheckupJournalEntry) -> None: ...
