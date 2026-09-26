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
from src.dropbox.services.entities.move_problem import MoveProblem
from src.dropbox.services.move_rollback.move_plan_rollback_result import (
    MovePlanRollbackResult,
)
from src.dropbox.services.move_rollback.protocols.i_dropbox_journal import (
    IDropboxJournal,
)
from src.dropbox.services.move_rollback.protocols.i_dropbox_move_boundary import (
    IDropboxMoveBoundary,
)
from src.dropbox.services.move_rollback.protocols.i_move_plan_store import (
    IMovePlanStore,
)

ROLLBACK_ALLOWED = (MovePlanStatus.EXECUTED, MovePlanStatus.PROPOSED)


class MovePlanRollback:
    def __init__(
        self,
        plans: IMovePlanStore,
        boundary: IDropboxMoveBoundary,
        journal: IDropboxJournal,
    ) -> None:
        self._plans = plans
        self._boundary = boundary
        self._journal = journal

    def rollback(self, plan_id: UUID) -> MovePlanRollbackResult:
        plan = self._rollbackable_plan(plan_id)
        performed = [
            PlannedMove(source=entry.source, target=entry.target)
            for entry in self._journal.plan_entries(plan_id)
            if entry.action == JournalAction.MOVED and entry.source is not None
        ]
        rolled_back: list[PlannedMove] = []
        skipped: list[MoveProblem] = []
        for move in reversed(performed):
            denial = self._boundary.move_denial(move.target, move.source)
            if denial is None:
                self._boundary.move(move.target, move.source)
                rolled_back.append(move)
                self._record(plan_id, JournalAction.MOVE_ROLLED_BACK, move, None)
            else:
                skipped.append(MoveProblem(move=move, reason=denial))
                self._record(plan_id, JournalAction.ROLLBACK_SKIPPED, move, denial)
        self._plans.update_status(plan_id, MovePlanStatus.ROLLED_BACK)
        return MovePlanRollbackResult(
            plan=plan.model_copy(update={"status": MovePlanStatus.ROLLED_BACK}),
            rolled_back=rolled_back,
            skipped=skipped,
        )

    def _record(
        self,
        plan_id: UUID,
        action: JournalAction,
        move: PlannedMove,
        reason: str | None,
    ) -> None:
        self._journal.append(
            JournalEntry(
                action=action,
                plan_id=plan_id,
                source=move.target,
                target=move.source,
                reason=reason,
                created_at=datetime.now(UTC),
            )
        )

    def _rollbackable_plan(self, plan_id: UUID) -> MovePlan:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise MovePlanNotFoundError(f"Плана переносов {plan_id} нет")
        if plan.status not in ROLLBACK_ALLOWED:
            raise MovePlanStatusError(
                f"План {plan_id} уже {plan.status.value}, откатить нельзя"
            )
        return plan
