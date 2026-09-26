from collections.abc import Mapping

from src.memory.models.whereabouts import Whereabouts
from src.memory.repos.formats.cell_reader import (
    optional_date_cell,
    required_date_cell,
    required_text_cell,
    text_cell,
)
from src.memory.repos.markdown_table.memory_date import format_memory_date
from src.memory.repos.markdown_table.row_rejection import RowRejection
from src.memory.repos.markdown_table.table_line import fold

SINCE = "С"
UNTIL = "По"
PLACE = "Где"
PURPOSE = "Что"
SOURCE = "Источник"


class WhereaboutsPageFormat:
    path = "Assistant/Где я буду.md"
    title = "Где я буду"
    columns = (SINCE, UNTIL, PLACE, PURPOSE, SOURCE)

    def key(self, entry: Whereabouts) -> tuple[str, ...]:
        return (entry.since.isoformat(), fold(entry.place))

    def describe(self, entry: Whereabouts) -> str:
        return f"{format_memory_date(entry.since)} · {entry.place}"

    def to_cells(self, entry: Whereabouts) -> list[str]:
        return [
            format_memory_date(entry.since),
            format_memory_date(entry.until),
            entry.place,
            entry.purpose,
            entry.source,
        ]

    def from_cells(self, cells: Mapping[str, str]) -> Whereabouts | RowRejection:
        since = required_date_cell(cells, SINCE)
        if isinstance(since, RowRejection):
            return since
        until = optional_date_cell(cells, UNTIL)
        if isinstance(until, RowRejection):
            return until
        place = required_text_cell(cells, PLACE)
        if isinstance(place, RowRejection):
            return place
        return Whereabouts(
            since=since,
            until=until,
            place=place,
            purpose=text_cell(cells, PURPOSE),
            source=text_cell(cells, SOURCE),
        )
