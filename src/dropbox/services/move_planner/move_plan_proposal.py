from pydantic import BaseModel

from src.dropbox.models.move_plan import MovePlan
from src.dropbox.services.entities.move_problem import MoveProblem


class MovePlanProposal(BaseModel):
    plan: MovePlan | None
    problems: list[MoveProblem]
