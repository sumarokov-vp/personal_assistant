from typing import Protocol

from src.checkup.services.checkup_actions.checkup_action_result import (
    CheckupActionResult,
)


class ICheckupSkipper(Protocol):
    def skip(self, raw_key: str, reason: str) -> CheckupActionResult: ...
