from collections.abc import Mapping

from src.memory.models.deadline import Deadline
from src.memory.repos.formats.cell_reader import (
    optional_date_cell,
    required_date_cell,
    required_text_cell,
    text_cell,
)
from src.memory.repos.markdown_table.memory_date import format_memory_date
from src.memory.repos.markdown_table.row_rejection import RowRejection
from src.memory.repos.markdown_table.table_line import fold

WHAT = "Что"
WHOSE = "Чьё"
EXPIRES = "Истекает"
RENEWAL = "Где и как продлевать"
DURATION = "Сколько занимает"
SOURCE = "Источник"
UPDATED = "Обновлено"


class DeadlinePageFormat:
    path = "Assistant/Реестр сроков.md"
    title = "Реестр сроков"
    columns = (WHAT, WHOSE, EXPIRES, RENEWAL, DURATION, SOURCE, UPDATED)

    def key(self, entry: Deadline) -> tuple[str, ...]:
        return (fold(entry.what), fold(entry.whose))

    def describe(self, entry: Deadline) -> str:
        return f"{entry.what} · {entry.whose}"

    def to_cells(self, entry: Deadline) -> list[str]:
        return [
            entry.what,
            entry.whose,
            format_memory_date(entry.expires),
            entry.renewal,
            entry.duration,
            entry.source,
            format_memory_date(entry.updated),
        ]

    def from_cells(self, cells: Mapping[str, str]) -> Deadline | RowRejection:
        what = required_text_cell(cells, WHAT)
        if isinstance(what, RowRejection):
            return what
        whose = required_text_cell(cells, WHOSE)
        if isinstance(whose, RowRejection):
            return whose
        expires = required_date_cell(cells, EXPIRES)
        if isinstance(expires, RowRejection):
            return expires
        updated = optional_date_cell(cells, UPDATED)
        if isinstance(updated, RowRejection):
            return updated
        return Deadline(
            what=what,
            whose=whose,
            expires=expires,
            renewal=text_cell(cells, RENEWAL),
            duration=text_cell(cells, DURATION),
            source=text_cell(cells, SOURCE),
            updated=updated,
        )
