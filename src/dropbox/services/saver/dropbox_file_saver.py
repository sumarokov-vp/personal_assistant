from datetime import UTC, datetime

from src.dropbox.models.journal_action import JournalAction
from src.dropbox.models.journal_entry import JournalEntry
from src.dropbox.services.saver.protocols.i_dropbox_journal_writer import (
    IDropboxJournalWriter,
)
from src.dropbox.services.saver.protocols.i_dropbox_write_boundary import (
    IDropboxWriteBoundary,
)


class DropboxFileSaver:
    def __init__(
        self, boundary: IDropboxWriteBoundary, journal: IDropboxJournalWriter
    ) -> None:
        self._boundary = boundary
        self._journal = journal

    def save(self, folder: str, name: str, content: bytes) -> str:
        saved_path = self._boundary.write_new_file(folder, name, content)
        self._journal.append(
            JournalEntry(
                action=JournalAction.ADDED,
                plan_id=None,
                source=None,
                target=saved_path,
                reason=None,
                created_at=datetime.now(UTC),
            )
        )
        return saved_path
