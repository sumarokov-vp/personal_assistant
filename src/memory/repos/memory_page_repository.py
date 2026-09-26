from src.memory.repos.markdown_table.markdown_page_parser import MarkdownPageParser
from src.memory.repos.markdown_table.markdown_page_renderer import (
    NEW_PAGE_NOTE,
    MarkdownPageRenderer,
)
from src.memory.repos.markdown_table.parsed_page import ParsedPage
from src.memory.repos.memory_page_format_error import MemoryPageFormatError
from src.memory.repos.memory_page_read import MemoryPageRead
from src.memory.repos.protocols.i_page_format import IPageFormat
from src.memory.repos.protocols.i_wiki_storage import IWikiStorage
from src.memory.repos.upsert_outcome import UpsertOutcome

_OUTCOME_VERB = {UpsertOutcome.CREATED: "добавлено", UpsertOutcome.UPDATED: "обновлено"}


class MemoryPageRepository[T]:
    def __init__(self, storage: IWikiStorage, page_format: IPageFormat[T]) -> None:
        self._storage = storage
        self._format = page_format
        self._parser = MarkdownPageParser()
        self._renderer = MarkdownPageRenderer()

    @property
    def path(self) -> str:
        return self._format.path

    def read(self) -> MemoryPageRead[T]:
        page = self._load()
        return MemoryPageRead(entries=list(page.entries), remarks=list(page.remarks))

    def find(self, key: tuple[str, ...]) -> T | None:
        return next(
            (entry for entry in self._load().entries if self._format.key(entry) == key),
            None,
        )

    def upsert(self, entry: T) -> UpsertOutcome:
        page = self._load()
        if not page.has_table:
            raise MemoryPageFormatError(self._format.path, page.remarks)
        key = self._format.key(entry)
        position = next(
            (
                index
                for index, existing in enumerate(page.entries)
                if self._format.key(existing) == key
            ),
            None,
        )
        if position is None:
            page.entries.append(entry)
            outcome = UpsertOutcome.CREATED
        else:
            page.entries[position] = entry
            outcome = UpsertOutcome.UPDATED
        message = f"память: {self._format.title} — {_OUTCOME_VERB[outcome]} «{self._format.describe(entry)}»"
        self._storage.write(
            self._format.path, self._renderer.render(page, self._format), message
        )
        return outcome

    def _load(self) -> ParsedPage[T]:
        text = self._storage.read(self._format.path)
        if text is None:
            return ParsedPage(has_table=True, prefix=[NEW_PAGE_NOTE, ""])
        return self._parser.parse(text, self._format)
