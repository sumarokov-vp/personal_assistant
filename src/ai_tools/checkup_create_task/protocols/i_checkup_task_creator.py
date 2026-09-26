from typing import Protocol

from src.checkup.services.checkup_actions.checkup_action_result import (
    CheckupActionResult,
)
from src.checkup.services.entities.checkup_run import CheckupRun


class ICheckupTaskCreator(Protocol):
    def create_task(
        self, raw_key: str, content: str, due: str, reason: str, run: CheckupRun
    ) -> CheckupActionResult: ...
