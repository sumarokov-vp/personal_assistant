from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

from src.dropbox.models.move_plan import MovePlan
from src.dropbox.models.move_plan_status import MovePlanStatus
from src.dropbox.models.planned_move import PlannedMove
from src.dropbox.services.move_planner.move_plan_proposal import MovePlanProposal
from src.dropbox.services.move_planner.protocols.i_move_plan_validator import (
    IMovePlanValidator,
)
from src.dropbox.services.move_planner.protocols.i_move_plan_writer import (
    IMovePlanWriter,
)


class MovePlanner:
    def __init__(self, validator: IMovePlanValidator, plans: IMovePlanWriter) -> None:
        self._validator = validator
        self._plans = plans

    def propose(self, owner_id: int, moves: Sequence[PlannedMove]) -> MovePlanProposal:
        if not moves:
            raise ValueError("План переносов пуст")
        problems = self._validator.problems(moves)
        if problems:
            return MovePlanProposal(plan=None, problems=problems)
        now = datetime.now(UTC)
        plan = MovePlan(
            id=uuid4(),
            owner_id=owner_id,
            status=MovePlanStatus.PROPOSED,
            moves=list(moves),
            created_at=now,
            updated_at=now,
        )
        self._plans.add(plan)
        return MovePlanProposal(plan=plan, problems=[])
