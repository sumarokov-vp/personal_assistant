from collections.abc import Sequence

from workers.memory_fill.memory_fill_report import MemoryFillReport
from workers.memory_fill.protocols.i_fill_conversation import IFillConversation
from workers.memory_fill.protocols.i_watched_page import IWatchedPage


class MemoryFillRun:
    def __init__(
        self,
        conversation: IFillConversation,
        pages: Sequence[IWatchedPage],
        thread_id: str,
        kickoff: str,
    ) -> None:
        self._conversation = conversation
        self._pages = pages
        self._thread_id = thread_id
        self._kickoff = kickoff

    def execute(self) -> MemoryFillReport:
        before = [page.snapshot() for page in self._pages]
        answer = self._conversation.process_message(self._thread_id, self._kickoff)
        return MemoryFillReport(
            pages=[
                page.changes_since(snapshot)
                for page, snapshot in zip(self._pages, before, strict=True)
            ],
            model_summary=answer.content or "",
        )
