from collections.abc import Sequence
from typing import Protocol

from src.dropbox.models.planned_move import PlannedMove
from src.dropbox.services.move_planner.move_plan_proposal import MovePlanProposal


class IMovePlanProposer(Protocol):
    def propose(
        self, owner_id: int, moves: Sequence[PlannedMove]
    ) -> MovePlanProposal: ...
