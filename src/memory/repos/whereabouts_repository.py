from datetime import date

from src.memory.models.whereabouts import Whereabouts
from src.memory.repos.formats.whereabouts_page_format import WhereaboutsPageFormat
from src.memory.repos.memory_page_read import MemoryPageRead
from src.memory.repos.memory_page_repository import MemoryPageRepository
from src.memory.repos.protocols.i_wiki_storage import IWikiStorage
from src.memory.repos.upsert_outcome import UpsertOutcome


class WhereaboutsRepository:
    def __init__(self, storage: IWikiStorage) -> None:
        self._format = WhereaboutsPageFormat()
        self._pages = MemoryPageRepository(storage, self._format)

    @property
    def path(self) -> str:
        return self._pages.path

    def read(self) -> MemoryPageRead[Whereabouts]:
        return self._pages.read()

    def find(self, since: date, place: str) -> Whereabouts | None:
        return self._pages.find(self._format.key_of(since, place))

    def upsert(self, whereabouts: Whereabouts) -> UpsertOutcome:
        return self._pages.upsert(whereabouts)
