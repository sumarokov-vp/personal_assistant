from src.memory.repos.markdown_table.parsed_page import ParsedPage
from src.memory.repos.markdown_table.row_rejection import RowRejection
from src.memory.repos.markdown_table.table_line import (
    fold,
    is_separator,
    is_table_line,
    split_cells,
)
from src.memory.repos.protocols.i_page_format import IPageFormat


class MarkdownPageParser:
    def parse[T](self, text: str, page_format: IPageFormat[T]) -> ParsedPage[T]:
        lines = text.splitlines()
        header_index = self._find_header(lines, page_format.columns)
        if header_index is None:
            columns = " | ".join(page_format.columns)
            return ParsedPage(
                has_table=False,
                prefix=lines,
                remarks=[f"не найдена таблица с колонками: {columns}"],
            )

        header = split_cells(lines[header_index])
        body_start = header_index + 1
        if body_start < len(lines) and is_separator(split_cells(lines[body_start])):
            body_start += 1
        body_end = body_start
        while body_end < len(lines) and is_table_line(lines[body_end]):
            body_end += 1

        page: ParsedPage[T] = ParsedPage(
            has_table=True,
            prefix=lines[:header_index],
            suffix=lines[body_end:],
            remarks=self._header_remarks(header, page_format.columns),
        )
        column_by_position = self._column_by_position(header, page_format.columns)
        seen_keys: set[tuple[str, ...]] = set()
        for line_number, raw in enumerate(
            lines[body_start:body_end], start=body_start + 1
        ):
            cells = split_cells(raw)
            if len(cells) != len(header):
                self._keep_foreign(
                    page,
                    line_number,
                    raw,
                    f"ячеек {len(cells)}, а колонок {len(header)}",
                )
                continue
            named_cells = {
                column_by_position[position]: cell
                for position, cell in enumerate(cells)
                if position in column_by_position
            }
            entry = page_format.from_cells(named_cells)
            if isinstance(entry, RowRejection):
                self._keep_foreign(page, line_number, raw, entry.reason)
                continue
            key = page_format.key(entry)
            if key in seen_keys:
                page.remarks.append(
                    f"строка {line_number}: повтор записи «{page_format.describe(entry)}» — upsert изменит первую"
                )
            seen_keys.add(key)
            page.entries.append(entry)
        return page

    def _find_header(self, lines: list[str], columns: tuple[str, ...]) -> int | None:
        required = {fold(column) for column in columns}
        for index, line in enumerate(lines):
            if is_table_line(line) and required <= {
                fold(cell) for cell in split_cells(line)
            }:
                return index
        return None

    def _column_by_position(
        self, header: list[str], columns: tuple[str, ...]
    ) -> dict[int, str]:
        canonical = {fold(column): column for column in columns}
        return {
            position: canonical[fold(cell)]
            for position, cell in enumerate(header)
            if fold(cell) in canonical
        }

    def _header_remarks(self, header: list[str], columns: tuple[str, ...]) -> list[str]:
        known = {fold(column) for column in columns}
        return [
            f"колонка «{cell}» не из формата страницы: при записи ассистентом её значения не сохранятся"
            for cell in header
            if fold(cell) not in known
        ]

    def _keep_foreign[T](
        self, page: ParsedPage[T], line_number: int, raw: str, reason: str
    ) -> None:
        page.foreign_rows.append(raw)
        page.remarks.append(
            f"строка {line_number} оставлена как есть ({reason}): {raw.strip()}"
        )
