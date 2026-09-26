from pydantic import BaseModel

from src.dropbox.models.move_plan import MovePlan
from src.dropbox.models.planned_move import PlannedMove
from src.dropbox.services.entities.move_problem import MoveProblem


class MovePlanRollbackResult(BaseModel):
    plan: MovePlan
    rolled_back: list[PlannedMove]
    skipped: list[MoveProblem]
