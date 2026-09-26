from pydantic import BaseModel

from src.dropbox.models.move_plan import MovePlan
from src.dropbox.models.planned_move import PlannedMove
from src.dropbox.services.entities.move_problem import MoveProblem


class MovePlanExecution(BaseModel):
    plan: MovePlan
    moved: list[PlannedMove]
    problems: list[MoveProblem]
