from bot_framework.core.entities.button import Button
from bot_framework.core.entities.keyboard import Keyboard
from bot_framework.core.protocols.i_message_replacer import IMessageReplacer
from bot_framework.core.protocols.i_message_sender import IMessageSender
from bot_framework.domain.language_management.repos.protocols.i_phrase_repo import (
    IPhraseRepo,
)

from src.dropbox.models.move_plan import MovePlan
from src.dropbox.services.move_executor.move_plan_execution import MovePlanExecution
from src.dropbox.services.move_rollback.move_plan_rollback_result import (
    MovePlanRollbackResult,
)
from src.flows.dropbox_moves.card.move_plan_callback import MovePlanCallback
from src.flows.dropbox_moves.card.move_plan_callbacks import (
    CANCEL_CALLBACK,
    EXECUTE_CALLBACK,
    ROLLBACK_CALLBACK,
)
from src.flows.dropbox_moves.card.move_plan_card_text import MovePlanCardText


class MovePlanCardPresenter:
    def __init__(
        self,
        message_sender: IMessageSender,
        message_replacer: IMessageReplacer,
        card_text: MovePlanCardText,
        phrase_repo: IPhraseRepo,
        language_code: str,
    ) -> None:
        self._message_sender = message_sender
        self._message_replacer = message_replacer
        self._card_text = card_text
        self._phrase_repo = phrase_repo
        self._language_code = language_code

    def send_proposal(self, chat_id: int, plan: MovePlan) -> None:
        self._message_sender.send(
            chat_id=chat_id,
            text=self._card_text.proposal(plan),
            keyboard=self._proposal_keyboard(plan),
        )

    def send_rollback_offer(self, chat_id: int, plan: MovePlan) -> None:
        self._message_sender.send(
            chat_id=chat_id,
            text=self._card_text.rollback_offer(plan),
            keyboard=self._rollback_keyboard(plan),
        )

    def show_execution(
        self, chat_id: int, message_id: int, execution: MovePlanExecution
    ) -> None:
        keyboard = (
            self._proposal_keyboard(execution.plan)
            if execution.problems
            else self._rollback_keyboard(execution.plan)
        )
        self._message_replacer.replace(
            chat_id=chat_id,
            message_id=message_id,
            text=self._card_text.execution(execution),
            keyboard=keyboard,
        )

    def show_rollback(
        self, chat_id: int, message_id: int, result: MovePlanRollbackResult
    ) -> None:
        self._message_replacer.replace(
            chat_id=chat_id,
            message_id=message_id,
            text=self._card_text.rollback(result),
        )

    def show_cancelled(self, chat_id: int, message_id: int, plan: MovePlan) -> None:
        self._message_replacer.replace(
            chat_id=chat_id,
            message_id=message_id,
            text=self._card_text.cancelled(plan),
        )

    def _proposal_keyboard(self, plan: MovePlan) -> Keyboard:
        return Keyboard(
            rows=[
                [
                    self._button(
                        "dropbox_moves.button.execute", EXECUTE_CALLBACK, plan
                    ),
                    self._button("dropbox_moves.button.cancel", CANCEL_CALLBACK, plan),
                ]
            ]
        )

    def _rollback_keyboard(self, plan: MovePlan) -> Keyboard:
        return Keyboard(
            rows=[
                [self._button("dropbox_moves.button.rollback", ROLLBACK_CALLBACK, plan)]
            ]
        )

    def _button(self, key: str, callback: MovePlanCallback, plan: MovePlan) -> Button:
        return Button(
            text=self._phrase_repo.get_phrase(
                key=key, language_code=self._language_code
            ),
            callback_data=callback.data(plan.id),
        )
