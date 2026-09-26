from bot_framework.core.entities.bot_callback import BotCallback
from bot_framework.core.protocols.i_callback_answerer import ICallbackAnswerer

from src.dropbox.models.move_plan_status import MovePlanStatus
from src.flows.dropbox_moves.card.move_plan_callbacks import EXECUTE_CALLBACK
from src.flows.dropbox_moves.handlers.protocols.i_execution_card_updater import (
    IExecutionCardUpdater,
)
from src.flows.dropbox_moves.handlers.protocols.i_move_plan_callback_guard import (
    IMovePlanCallbackGuard,
)
from src.flows.dropbox_moves.handlers.protocols.i_move_plan_executor import (
    IMovePlanExecutor,
)


class ExecuteMovePlanHandler:
    def __init__(
        self,
        callback_answerer: ICallbackAnswerer,
        guard: IMovePlanCallbackGuard,
        executor: IMovePlanExecutor,
        card: IExecutionCardUpdater,
    ) -> None:
        self.callback_answerer = callback_answerer
        self._guard = guard
        self._executor = executor
        self._card = card
        self.prefix = EXECUTE_CALLBACK.prefix
        self.allowed_roles: set[str] | None = {"admin"}

    def handle(self, callback: BotCallback) -> None:
        press = self._guard.resolve(callback, EXECUTE_CALLBACK, MovePlanStatus.PROPOSED)
        if press is None:
            return
        self.callback_answerer.answer(callback_query_id=callback.id)
        execution = self._executor.execute(press.plan.id)
        self._card.show_execution(press.chat_id, press.message_id, execution)
