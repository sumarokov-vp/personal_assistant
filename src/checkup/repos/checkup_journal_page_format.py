from collections.abc import Mapping

from src.checkup.models.checkup_journal_entry import CheckupJournalEntry
from src.checkup.models.checkup_key import KEY_FORMAT, CheckupKey
from src.memory.repos.formats.cell_reader import (
    required_date_cell,
    required_text_cell,
    text_cell,
)
from src.memory.repos.markdown_table.memory_date import format_memory_date
from src.memory.repos.markdown_table.row_rejection import RowRejection
from src.memory.repos.markdown_table.table_line import fold

KEY = "Ключ"
WHEN = "Когда"
DONE = "Что сделано"
TASK = "Задача Todoist"
REASON = "Причина"


class CheckupJournalPageFormat:
    path = "Assistant/Журнал чекапа.md"
    title = "Журнал чекапа"
    columns = (KEY, WHEN, DONE, TASK, REASON)

    def key(self, entry: CheckupJournalEntry) -> tuple[str, ...]:
        return self.key_of(entry.key)

    def key_of(self, key_text: str) -> tuple[str, ...]:
        return (fold(key_text),)

    def describe(self, entry: CheckupJournalEntry) -> str:
        return entry.key

    def to_cells(self, entry: CheckupJournalEntry) -> list[str]:
        return [
            entry.key,
            format_memory_date(entry.when),
            entry.done,
            entry.task,
            entry.reason,
        ]

    def from_cells(
        self, cells: Mapping[str, str]
    ) -> CheckupJournalEntry | RowRejection:
        key = CheckupKey.parse(text_cell(cells, KEY))
        if key is None:
            return RowRejection(f"ключ не в формате «{KEY_FORMAT}»")
        when = required_date_cell(cells, WHEN)
        if isinstance(when, RowRejection):
            return when
        done = required_text_cell(cells, DONE)
        if isinstance(done, RowRejection):
            return done
        return CheckupJournalEntry(
            key=key.text,
            when=when,
            done=done,
            task=text_cell(cells, TASK),
            reason=text_cell(cells, REASON),
        )
