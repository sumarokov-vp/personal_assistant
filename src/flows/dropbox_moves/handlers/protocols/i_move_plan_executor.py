from typing import Protocol
from uuid import UUID

from src.dropbox.services.move_executor.move_plan_execution import MovePlanExecution


class IMovePlanExecutor(Protocol):
    def execute(self, plan_id: UUID) -> MovePlanExecution: ...
