from typing import Protocol

from bot_framework.core.entities.bot_callback import BotCallback

from src.dropbox.models.move_plan_status import MovePlanStatus
from src.flows.dropbox_moves.card.move_plan_callback import MovePlanCallback
from src.flows.dropbox_moves.services.callback_guard.move_plan_card_press import (
    MovePlanCardPress,
)


class IMovePlanCallbackGuard(Protocol):
    def resolve(
        self,
        callback: BotCallback,
        button: MovePlanCallback,
        expected_status: MovePlanStatus,
    ) -> MovePlanCardPress | None: ...
