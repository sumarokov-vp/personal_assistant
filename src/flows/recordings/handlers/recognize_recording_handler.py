from bot_framework.core.entities.bot_callback import BotCallback
from bot_framework.core.protocols.i_callback_answerer import ICallbackAnswerer

from src.flows.recordings.card.recording_callbacks import RECOGNIZE_CALLBACK
from src.flows.recordings.handlers.protocols.i_recognizing_card_updater import (
    IRecognizingCardUpdater,
)
from src.flows.recordings.handlers.protocols.i_recording_transcriber import (
    IRecordingTranscriber,
)
from src.flows.recordings.handlers.recording_callback_guard import (
    RecordingCallbackGuard,
)


class RecognizeRecordingHandler:
    def __init__(
        self,
        callback_answerer: ICallbackAnswerer,
        guard: RecordingCallbackGuard,
        card: IRecognizingCardUpdater,
        transcriber: IRecordingTranscriber,
    ) -> None:
        self.callback_answerer = callback_answerer
        self._guard = guard
        self._card = card
        self._transcriber = transcriber
        self.prefix = RECOGNIZE_CALLBACK.prefix
        self.allowed_roles: set[str] | None = {"admin"}

    def handle(self, callback: BotCallback) -> None:
        press = self._guard.take(callback, RECOGNIZE_CALLBACK)
        if press is None:
            return
        recording = press.pending.recording
        self._card.show_recognizing(
            press.chat_id, press.message_id, recording.file_name, recording.size_bytes
        )
        self._transcriber.transcribe(
            file_id=recording.file_id,
            file_name=recording.file_name,
            size_bytes=recording.size_bytes,
            chat_id=press.chat_id,
            card_message_id=press.message_id,
        )
