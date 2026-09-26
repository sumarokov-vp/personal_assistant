from src.checkup.models.checkup_journal_entry import CheckupJournalEntry
from src.checkup.repos.checkup_journal_page_format import CheckupJournalPageFormat
from src.memory.repos.markdown_table.markdown_page_parser import MarkdownPageParser
from src.memory.repos.memory_page_format_error import MemoryPageFormatError
from src.memory.repos.memory_page_repository import MemoryPageRepository
from src.memory.repos.protocols.i_wiki_storage import IWikiStorage


class CheckupJournalRepository:
    def __init__(self, storage: IWikiStorage) -> None:
        self._storage = storage
        self._format = CheckupJournalPageFormat()
        self._parser = MarkdownPageParser()
        self._pages = MemoryPageRepository(storage, self._format)

    def find(self, key_text: str) -> CheckupJournalEntry | None:
        text = self._storage.read(self._format.path)
        if text is None:
            return None
        page = self._parser.parse(text, self._format)
        if not page.has_table:
            raise MemoryPageFormatError(self._format.path, page.remarks)
        wanted = self._format.key_of(key_text)
        return next(
            (entry for entry in page.entries if self._format.key(entry) == wanted),
            None,
        )

    def record(self, entry: CheckupJournalEntry) -> None:
        self._pages.upsert(entry)
