from uuid import UUID

from src.dropbox.models.move_plan import MovePlan
from src.dropbox.models.move_plan_status import MovePlanStatus


class InMemoryMovePlanStore:
    def __init__(self) -> None:
        self._plans: dict[UUID, MovePlan] = {}

    def add(self, plan: MovePlan) -> None:
        self._plans[plan.id] = plan

    def get(self, plan_id: UUID) -> MovePlan | None:
        return self._plans.get(plan_id)

    def update_status(self, plan_id: UUID, status: MovePlanStatus) -> None:
        self._plans[plan_id] = self._plans[plan_id].model_copy(
            update={"status": status}
        )
