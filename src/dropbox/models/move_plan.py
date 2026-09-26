from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.dropbox.models.move_plan_status import MovePlanStatus
from src.dropbox.models.planned_move import PlannedMove


class MovePlan(BaseModel):
    id: UUID
    owner_id: int
    status: MovePlanStatus
    moves: list[PlannedMove]
    created_at: datetime
    updated_at: datetime
