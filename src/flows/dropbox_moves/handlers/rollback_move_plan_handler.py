from bot_framework.core.entities.bot_callback import BotCallback
from bot_framework.core.protocols.i_callback_answerer import ICallbackAnswerer

from src.dropbox.models.move_plan_status import MovePlanStatus
from src.flows.dropbox_moves.card.move_plan_callbacks import ROLLBACK_CALLBACK
from src.flows.dropbox_moves.handlers.protocols.i_move_plan_callback_guard import (
    IMovePlanCallbackGuard,
)
from src.flows.dropbox_moves.handlers.protocols.i_move_plan_rollback import (
    IMovePlanRollback,
)
from src.flows.dropbox_moves.handlers.protocols.i_rollback_card_updater import (
    IRollbackCardUpdater,
)


class RollbackMovePlanHandler:
    def __init__(
        self,
        callback_answerer: ICallbackAnswerer,
        guard: IMovePlanCallbackGuard,
        rollback: IMovePlanRollback,
        card: IRollbackCardUpdater,
    ) -> None:
        self.callback_answerer = callback_answerer
        self._guard = guard
        self._rollback = rollback
        self._card = card
        self.prefix = ROLLBACK_CALLBACK.prefix
        self.allowed_roles: set[str] | None = {"admin"}

    def handle(self, callback: BotCallback) -> None:
        press = self._guard.resolve(
            callback, ROLLBACK_CALLBACK, MovePlanStatus.EXECUTED
        )
        if press is None:
            return
        self.callback_answerer.answer(callback_query_id=callback.id)
        result = self._rollback.rollback(press.plan.id)
        self._card.show_rollback(press.chat_id, press.message_id, result)
