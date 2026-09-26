from typing import Protocol

from src.dropbox.models.move_plan import MovePlan


class IRollbackOfferSender(Protocol):
    def send_rollback_offer(self, chat_id: int, plan: MovePlan) -> None: ...
