import logging

from bot_framework.core.entities.bot_callback import BotCallback
from bot_framework.core.protocols.i_callback_answerer import ICallbackAnswerer
from bot_framework.domain.language_management.repos.protocols.i_phrase_repo import (
    IPhraseRepo,
)

from src.dropbox.models.move_plan_status import MovePlanStatus
from src.flows.dropbox_moves.card.move_plan_callback import MovePlanCallback
from src.flows.dropbox_moves.services.callback_guard.move_plan_card_press import (
    MovePlanCardPress,
)
from src.flows.dropbox_moves.services.callback_guard.protocols.i_move_plan_reader import (
    IMovePlanReader,
)

logger = logging.getLogger(__name__)


class MovePlanCallbackGuard:
    def __init__(
        self,
        callback_answerer: ICallbackAnswerer,
        plans: IMovePlanReader,
        phrase_repo: IPhraseRepo,
        language_code: str,
    ) -> None:
        self._callback_answerer = callback_answerer
        self._plans = plans
        self._phrase_repo = phrase_repo
        self._language_code = language_code

    def resolve(
        self,
        callback: BotCallback,
        button: MovePlanCallback,
        expected_status: MovePlanStatus,
    ) -> MovePlanCardPress | None:
        plan_id = button.plan_id(callback.data)
        if plan_id is None or not callback.message_chat_id or not callback.message_id:
            logger.warning(
                "dropbox_moves: malformed callback user_id=%s data=%r",
                callback.user_id,
                callback.data,
            )
            self._alert(callback, "dropbox_moves.alert.stale")
            return None
        plan = self._plans.get(plan_id)
        if plan is None:
            self._alert(callback, "dropbox_moves.alert.not_found")
            return None
        if plan.owner_id != callback.user_id:
            logger.warning(
                "dropbox_moves: owner mismatch user_id=%s owner_id=%s plan_id=%s",
                callback.user_id,
                plan.owner_id,
                plan.id,
            )
            self._alert(callback, "dropbox_moves.alert.not_owner")
            return None
        if plan.status != expected_status:
            self._alert(callback, f"dropbox_moves.alert.already_{plan.status.value}")
            return None
        return MovePlanCardPress(
            plan=plan,
            chat_id=callback.message_chat_id,
            message_id=callback.message_id,
        )

    def _alert(self, callback: BotCallback, key: str) -> None:
        self._callback_answerer.answer(
            callback_query_id=callback.id,
            text=self._phrase_repo.get_phrase(
                key=key, language_code=self._language_code
            ),
            show_alert=True,
        )
