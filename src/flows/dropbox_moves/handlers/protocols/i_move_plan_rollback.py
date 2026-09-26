from typing import Protocol
from uuid import UUID

from src.dropbox.services.move_rollback.move_plan_rollback_result import (
    MovePlanRollbackResult,
)


class IMovePlanRollback(Protocol):
    def rollback(self, plan_id: UUID) -> MovePlanRollbackResult: ...
