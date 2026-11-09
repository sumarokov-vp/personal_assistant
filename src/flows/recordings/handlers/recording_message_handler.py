from bot_framework import BotMessage, IMessageSender, check_message_roles
from bot_framework.domain.role_management.repos import RoleRepo

from src.flows.recordings.handlers.pending.pending_recordings import (
    PendingRecordings,
)
from src.flows.recordings.handlers.protocols.i_recording_question_card import (
    IRecordingQuestionCard,
)
from src.flows.recordings.handlers.recording_file_detector import (
    RecordingFileDetector,
)

DEFAULT_RECORDING_MAX_BYTES = 20 * 1024 * 1024


class RecordingMessageHandler:
    allowed_roles: set[str] | None = {"admin"}

    def __init__(
        self,
        detector: RecordingFileDetector,
        pending: PendingRecordings,
        card: IRecordingQuestionCard,
        message_sender: IMessageSender,
        role_repo: RoleRepo,
        max_bytes: int,
    ) -> None:
        self._detector = detector
        self._pending = pending
        self._card = card
        self.message_sender = message_sender
        self.role_repo = role_repo
        self._max_bytes = max_bytes

    @check_message_roles
    def handle(self, message: BotMessage) -> None:
        recording = self._detector.recording_of(message.get_original())
        if recording is None:
            return
        if recording.size_bytes > self._max_bytes:
            self._card.send_too_large(
                message.chat_id,
                recording.file_name,
                recording.size_bytes,
                self._max_bytes,
            )
            return
        pending = self._pending.add(message.chat_id, recording)
        self._card.send_question(
            message.chat_id,
            pending.intake_id,
            recording.file_name,
            recording.size_bytes,
        )
