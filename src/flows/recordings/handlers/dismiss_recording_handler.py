from bot_framework.core.entities.bot_callback import BotCallback
from bot_framework.core.protocols.i_callback_answerer import ICallbackAnswerer

from src.flows.recordings.card.recording_callbacks import DISMISS_CALLBACK
from src.flows.recordings.handlers.protocols.i_dismissed_card_updater import (
    IDismissedCardUpdater,
)
from src.flows.recordings.handlers.recording_callback_guard import (
    RecordingCallbackGuard,
)


class DismissRecordingHandler:
    def __init__(
        self,
        callback_answerer: ICallbackAnswerer,
        guard: RecordingCallbackGuard,
        card: IDismissedCardUpdater,
    ) -> None:
        self.callback_answerer = callback_answerer
        self._guard = guard
        self._card = card
        self.prefix = DISMISS_CALLBACK.prefix
        self.allowed_roles: set[str] | None = {"admin"}

    def handle(self, callback: BotCallback) -> None:
        press = self._guard.take(callback, DISMISS_CALLBACK)
        if press is None:
            return
        recording = press.pending.recording
        self._card.show_dismissed(
            press.chat_id, press.message_id, recording.file_name, recording.size_bytes
        )
