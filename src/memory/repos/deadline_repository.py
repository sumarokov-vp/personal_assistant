from src.memory.models.deadline import Deadline
from src.memory.repos.formats.deadline_page_format import DeadlinePageFormat
from src.memory.repos.memory_page_read import MemoryPageRead
from src.memory.repos.memory_page_repository import MemoryPageRepository
from src.memory.repos.protocols.i_wiki_storage import IWikiStorage
from src.memory.repos.upsert_outcome import UpsertOutcome


class DeadlineRepository:
    def __init__(self, storage: IWikiStorage) -> None:
        self._format = DeadlinePageFormat()
        self._pages = MemoryPageRepository(storage, self._format)

    @property
    def path(self) -> str:
        return self._pages.path

    def read(self) -> MemoryPageRead[Deadline]:
        return self._pages.read()

    def find(self, what: str, whose: str) -> Deadline | None:
        return self._pages.find(self._format.key_of(what, whose))

    def upsert(self, deadline: Deadline) -> UpsertOutcome:
        return self._pages.upsert(deadline)
