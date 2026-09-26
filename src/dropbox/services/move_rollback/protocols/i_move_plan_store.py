from typing import Protocol
from uuid import UUID

from src.dropbox.models.move_plan import MovePlan
from src.dropbox.models.move_plan_status import MovePlanStatus


class IMovePlanStore(Protocol):
    def get(self, plan_id: UUID) -> MovePlan | None: ...

    def update_status(self, plan_id: UUID, status: MovePlanStatus) -> None: ...
