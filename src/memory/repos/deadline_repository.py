from src.memory.models.deadline import Deadline
from src.memory.repos.formats.deadline_page_format import DeadlinePageFormat
from src.memory.repos.memory_page_read import MemoryPageRead
from src.memory.repos.memory_page_repository import MemoryPageRepository
from src.memory.repos.protocols.i_wiki_storage import IWikiStorage
from src.memory.repos.upsert_outcome import UpsertOutcome


class DeadlineRepository:
    def __init__(self, storage: IWikiStorage) -> None:
        self._pages = MemoryPageRepository(storage, DeadlinePageFormat())

    def read(self) -> MemoryPageRead[Deadline]:
        return self._pages.read()

    def upsert(self, deadline: Deadline) -> UpsertOutcome:
        return self._pages.upsert(deadline)
