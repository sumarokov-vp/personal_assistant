from collections.abc import Sequence
from typing import Protocol

from src.dropbox.models.planned_move import PlannedMove
from src.dropbox.services.entities.move_problem import MoveProblem


class IMovePlanValidator(Protocol):
    def problems(self, moves: Sequence[PlannedMove]) -> list[MoveProblem]: ...
