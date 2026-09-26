from collections.abc import Mapping

from src.memory.models.commitment import Commitment
from src.memory.models.commitment_status import CommitmentStatus
from src.memory.repos.formats.cell_reader import (
    optional_date_cell,
    required_text_cell,
    text_cell,
)
from src.memory.repos.markdown_table.memory_date import format_memory_date
from src.memory.repos.markdown_table.row_rejection import RowRejection
from src.memory.repos.markdown_table.table_line import fold

WHAT = "Что"
PARTIES = "Кто кому"
DUE = "Срок"
STATUS = "Статус"
SOURCE = "Источник"


class CommitmentPageFormat:
    path = "Assistant/Обязательства.md"
    title = "Обязательства"
    columns = (WHAT, PARTIES, DUE, STATUS, SOURCE)

    def key(self, entry: Commitment) -> tuple[str, ...]:
        return self.key_of(entry.what, entry.parties)

    def key_of(self, what: str, parties: str) -> tuple[str, ...]:
        return (fold(what), fold(parties))

    def describe(self, entry: Commitment) -> str:
        return f"{entry.what} · {entry.parties}"

    def to_cells(self, entry: Commitment) -> list[str]:
        return [
            entry.what,
            entry.parties,
            format_memory_date(entry.due),
            entry.status.value,
            entry.source,
        ]

    def from_cells(self, cells: Mapping[str, str]) -> Commitment | RowRejection:
        what = required_text_cell(cells, WHAT)
        if isinstance(what, RowRejection):
            return what
        parties = required_text_cell(cells, PARTIES)
        if isinstance(parties, RowRejection):
            return parties
        due = optional_date_cell(cells, DUE)
        if isinstance(due, RowRejection):
            return due
        status = self._status(text_cell(cells, STATUS))
        if isinstance(status, RowRejection):
            return status
        return Commitment(
            what=what,
            parties=parties,
            due=due,
            status=status,
            source=text_cell(cells, SOURCE),
        )

    def _status(self, text: str) -> CommitmentStatus | RowRejection:
        if not text:
            return CommitmentStatus.OPEN
        for status in CommitmentStatus:
            if fold(text) == status.value:
                return status
        allowed = ", ".join(status.value for status in CommitmentStatus)
        return RowRejection(f"статус «{text}» не из списка: {allowed}")
