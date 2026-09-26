from bot_framework.core.entities.bot_callback import BotCallback
from bot_framework.core.protocols.i_callback_answerer import ICallbackAnswerer

from src.dropbox.models.move_plan_status import MovePlanStatus
from src.flows.dropbox_moves.card.move_plan_callbacks import CANCEL_CALLBACK
from src.flows.dropbox_moves.handlers.protocols.i_cancelled_card_updater import (
    ICancelledCardUpdater,
)
from src.flows.dropbox_moves.handlers.protocols.i_move_plan_callback_guard import (
    IMovePlanCallbackGuard,
)
from src.flows.dropbox_moves.handlers.protocols.i_move_plan_canceller import (
    IMovePlanCanceller,
)


class CancelMovePlanHandler:
    def __init__(
        self,
        callback_answerer: ICallbackAnswerer,
        guard: IMovePlanCallbackGuard,
        canceller: IMovePlanCanceller,
        card: ICancelledCardUpdater,
    ) -> None:
        self.callback_answerer = callback_answerer
        self._guard = guard
        self._canceller = canceller
        self._card = card
        self.prefix = CANCEL_CALLBACK.prefix
        self.allowed_roles: set[str] | None = {"admin"}

    def handle(self, callback: BotCallback) -> None:
        press = self._guard.resolve(callback, CANCEL_CALLBACK, MovePlanStatus.PROPOSED)
        if press is None:
            return
        self.callback_answerer.answer(callback_query_id=callback.id)
        self._canceller.cancel(press.plan.id)
        self._card.show_cancelled(press.chat_id, press.message_id, press.plan)
