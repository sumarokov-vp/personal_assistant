from typing import Protocol

from src.dropbox.models.move_plan import MovePlan


class IMovePlanCardSender(Protocol):
    def send_proposal(self, chat_id: int, plan: MovePlan) -> None: ...
