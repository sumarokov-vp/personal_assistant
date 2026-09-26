from typing import Protocol

from src.dropbox.models.move_plan import MovePlan


class ICancelledCardUpdater(Protocol):
    def show_cancelled(self, chat_id: int, message_id: int, plan: MovePlan) -> None: ...
