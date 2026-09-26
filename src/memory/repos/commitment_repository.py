from src.memory.models.commitment import Commitment
from src.memory.models.commitment_status import CommitmentStatus
from src.memory.repos.formats.commitment_page_format import CommitmentPageFormat
from src.memory.repos.memory_page_read import MemoryPageRead
from src.memory.repos.memory_page_repository import MemoryPageRepository
from src.memory.repos.protocols.i_wiki_storage import IWikiStorage
from src.memory.repos.upsert_outcome import UpsertOutcome


class CommitmentRepository:
    def __init__(self, storage: IWikiStorage) -> None:
        self._format = CommitmentPageFormat()
        self._pages = MemoryPageRepository(storage, self._format)

    def read(self) -> MemoryPageRead[Commitment]:
        return self._pages.read()

    def upsert(self, commitment: Commitment) -> UpsertOutcome:
        return self._pages.upsert(commitment)

    def close(self, what: str, parties: str) -> Commitment | None:
        found = self._pages.find(self._format.key_of(what, parties))
        if found is None:
            return None
        closed = found.model_copy(update={"status": CommitmentStatus.DONE})
        self._pages.upsert(closed)
        return closed
