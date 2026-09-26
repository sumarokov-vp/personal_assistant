from typing import Protocol
from uuid import UUID


class IMovePlanCanceller(Protocol):
    def cancel(self, plan_id: UUID) -> None: ...
