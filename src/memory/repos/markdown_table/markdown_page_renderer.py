from src.memory.repos.markdown_table.parsed_page import ParsedPage
from src.memory.repos.markdown_table.table_line import join_cells
from src.memory.repos.protocols.i_page_format import IPageFormat

NEW_PAGE_NOTE = "Ведёт ассистент, колонки не переименовывать."


class MarkdownPageRenderer:
    def render[T](self, page: ParsedPage[T], page_format: IPageFormat[T]) -> str:
        columns = list(page_format.columns)
        table = [
            join_cells(columns),
            join_cells(["---"] * len(columns)),
            *(join_cells(page_format.to_cells(entry)) for entry in page.entries),
            *page.foreign_rows,
        ]
        return "\n".join([*page.prefix, *table, *page.suffix]) + "\n"
