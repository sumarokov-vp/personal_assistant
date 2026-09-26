from datetime import UTC, datetime
from uuid import UUID

from src.dropbox.models.journal_action import JournalAction
from src.dropbox.models.journal_entry import JournalEntry
from src.dropbox.models.move_plan import MovePlan
from src.dropbox.models.move_plan_status import MovePlanStatus
from src.dropbox.models.planned_move import PlannedMove
from src.dropbox.services.entities.move_plan_not_found_error import (
    MovePlanNotFoundError,
)
from src.dropbox.services.entities.move_plan_status_error import MovePlanStatusError
from src.dropbox.services.move_executor.move_plan_execution import MovePlanExecution
from src.dropbox.services.move_executor.protocols.i_dropbox_journal_writer import (
    IDropboxJournalWriter,
)
from src.dropbox.services.move_executor.protocols.i_dropbox_mover import (
    IDropboxMover,
)
from src.dropbox.services.move_executor.protocols.i_move_plan_store import (
    IMovePlanStore,
)
from src.dropbox.services.move_executor.protocols.i_move_plan_validator import (
    IMovePlanValidator,
)


class MovePlanExecutor:
    def __init__(
        self,
        plans: IMovePlanStore,
        validator: IMovePlanValidator,
        boundary: IDropboxMover,
        journal: IDropboxJournalWriter,
    ) -> None:
        self._plans = plans
        self._validator = validator
        self._boundary = boundary
        self._journal = journal

    def execute(self, plan_id: UUID) -> MovePlanExecution:
        plan = self._proposed_plan(plan_id)
        problems = self._validator.problems(plan.moves)
        if problems:
            return MovePlanExecution(plan=plan, moved=[], problems=problems)
        moved = [self._move(plan.id, move) for move in plan.moves]
        self._plans.update_status(plan.id, MovePlanStatus.EXECUTED)
        executed = plan.model_copy(update={"status": MovePlanStatus.EXECUTED})
        return MovePlanExecution(plan=executed, moved=moved, problems=[])

    def _move(self, plan_id: UUID, move: PlannedMove) -> PlannedMove:
        target = self._boundary.move(move.source, move.target)
        self._journal.append(
            JournalEntry(
                action=JournalAction.MOVED,
                plan_id=plan_id,
                source=move.source,
                target=target,
                reason=None,
                created_at=datetime.now(UTC),
            )
        )
        return PlannedMove(source=move.source, target=target)

    def _proposed_plan(self, plan_id: UUID) -> MovePlan:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise MovePlanNotFoundError(f"Плана переносов {plan_id} нет")
        if plan.status != MovePlanStatus.PROPOSED:
            raise MovePlanStatusError(
                f"План {plan_id} уже {plan.status.value}, выполнить можно только предложенный"
            )
        return plan
