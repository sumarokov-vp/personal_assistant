from uuid import UUID

from src.dropbox.models.move_plan_status import MovePlanStatus
from src.dropbox.services.entities.move_plan_not_found_error import (
    MovePlanNotFoundError,
)
from src.dropbox.services.entities.move_plan_status_error import MovePlanStatusError
from src.dropbox.services.move_canceller.protocols.i_move_plan_store import (
    IMovePlanStore,
)


class MovePlanCanceller:
    def __init__(self, plans: IMovePlanStore) -> None:
        self._plans = plans

    def cancel(self, plan_id: UUID) -> None:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise MovePlanNotFoundError(f"Плана переносов {plan_id} нет")
        if plan.status != MovePlanStatus.PROPOSED:
            raise MovePlanStatusError(
                f"План {plan_id} уже {plan.status.value}, отменить можно только предложенный"
            )
        self._plans.update_status(plan_id, MovePlanStatus.CANCELLED)
