from typing import Protocol
from uuid import UUID

from src.dropbox.models.move_plan import MovePlan


class IMovePlanReader(Protocol):
    def get(self, plan_id: UUID) -> MovePlan | None: ...
