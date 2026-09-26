from pydantic import BaseModel, ConfigDict

from src.dropbox.models.planned_move import PlannedMove


class MoveProblem(BaseModel):
    model_config = ConfigDict(frozen=True)

    move: PlannedMove
    reason: str
