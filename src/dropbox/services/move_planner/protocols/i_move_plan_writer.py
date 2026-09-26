from typing import Protocol

from src.dropbox.models.move_plan import MovePlan


class IMovePlanWriter(Protocol):
    def add(self, plan: MovePlan) -> None: ...
