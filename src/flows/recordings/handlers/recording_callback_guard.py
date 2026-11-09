import logging

from bot_framework.core.entities.bot_callback import BotCallback
from bot_framework.core.protocols.i_callback_answerer import ICallbackAnswerer

from src.flows.recordings.card.recording_callback import RecordingCallback
from src.flows.recordings.card.recording_card_text import (
    ALREADY_ANSWERED_TEXT,
    STALE_CARD_ALERT,
)
from src.flows.recordings.handlers.pending.pending_recordings import (
    PendingRecordings,
)
from src.flows.recordings.handlers.recording_card_press import RecordingCardPress

logger = logging.getLogger(__name__)


class RecordingCallbackGuard:
    def __init__(
        self, callback_answerer: ICallbackAnswerer, pending: PendingRecordings
    ) -> None:
        self._callback_answerer = callback_answerer
        self._pending = pending

    def take(
        self, callback: BotCallback, button: RecordingCallback
    ) -> RecordingCardPress | None:
        intake_id = button.intake_id(callback.data)
        if intake_id is None or not callback.message_chat_id or not callback.message_id:
            logger.warning(
                "recordings: malformed callback user_id=%s data=%r",
                callback.user_id,
                callback.data,
            )
            self._answer(callback, STALE_CARD_ALERT, show_alert=True)
            return None
        pending = self._pending.take(intake_id)
        if pending is not None:
            self._callback_answerer.answer(callback_query_id=callback.id)
            return RecordingCardPress(
                pending=pending,
                chat_id=callback.message_chat_id,
                message_id=callback.message_id,
            )
        if self._pending.was_answered(intake_id):
            self._answer(callback, ALREADY_ANSWERED_TEXT, show_alert=False)
            return None
        self._answer(callback, STALE_CARD_ALERT, show_alert=True)
        return None

    def _answer(self, callback: BotCallback, text: str, show_alert: bool) -> None:
        self._callback_answerer.answer(
            callback_query_id=callback.id, text=text, show_alert=show_alert
        )
