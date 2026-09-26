from collections.abc import Mapping
from datetime import date

from src.memory.repos.markdown_table.memory_date import parse_memory_date
from src.memory.repos.markdown_table.row_rejection import RowRejection


def text_cell(cells: Mapping[str, str], column: str) -> str:
    return " ".join(cells.get(column, "").split())


def required_text_cell(cells: Mapping[str, str], column: str) -> str | RowRejection:
    text = text_cell(cells, column)
    return text if text else RowRejection(f"пусто в колонке «{column}»")


def optional_date_cell(
    cells: Mapping[str, str], column: str
) -> date | None | RowRejection:
    text = text_cell(cells, column)
    if not text:
        return None
    parsed = parse_memory_date(text)
    if parsed is None:
        return RowRejection(f"в колонке «{column}» не дата ДД.ММ.ГГГГ: {text}")
    return parsed


def required_date_cell(cells: Mapping[str, str], column: str) -> date | RowRejection:
    parsed = optional_date_cell(cells, column)
    return RowRejection(f"пусто в колонке «{column}»") if parsed is None else parsed
