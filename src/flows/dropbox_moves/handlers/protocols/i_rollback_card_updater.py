from typing import Protocol

from src.dropbox.services.move_rollback.move_plan_rollback_result import (
    MovePlanRollbackResult,
)


class IRollbackCardUpdater(Protocol):
    def show_rollback(
        self, chat_id: int, message_id: int, result: MovePlanRollbackResult
    ) -> None: ...
