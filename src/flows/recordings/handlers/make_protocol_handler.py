import logging

from bot_framework.core.entities.bot_callback import BotCallback
from bot_framework.core.protocols.i_callback_answerer import ICallbackAnswerer

from src.flows.recordings.card.recording_card_text import STALE_CARD_ALERT
from src.flows.recordings.handlers.outcome_message_transcript_path import (
    OutcomeMessageTranscriptPath,
)
from src.flows.recordings.handlers.protocols.i_protocol_starter import (
    IProtocolStarter,
)
from src.flows.recordings.services.entities.protocol_callback import ProtocolCallback
from src.flows.recordings.services.entities.protocol_request import ProtocolRequest

logger = logging.getLogger(__name__)


class MakeProtocolHandler:
    def __init__(
        self,
        callback_answerer: ICallbackAnswerer,
        protocol_callback: ProtocolCallback,
        transcript_path: OutcomeMessageTranscriptPath,
        starter: IProtocolStarter,
    ) -> None:
        self.callback_answerer = callback_answerer
        self._protocol_callback = protocol_callback
        self._transcript_path = transcript_path
        self._starter = starter
        self.prefix = protocol_callback.prefix
        self.allowed_roles: set[str] | None = {"admin"}

    def handle(self, callback: BotCallback) -> None:
        parsed = self._protocol_callback.parse(callback.data)
        if parsed is None or not callback.message_chat_id:
            logger.warning(
                "recordings: malformed protocol callback user_id=%s data=%r",
                callback.user_id,
                callback.data,
            )
            self.callback_answerer.answer(
                callback_query_id=callback.id, text=STALE_CARD_ALERT, show_alert=True
            )
            return
        self.callback_answerer.answer(callback_query_id=callback.id)
        kind, transcript_id = parsed
        self._starter.start(
            ProtocolRequest(
                chat_id=callback.message_chat_id,
                transcript_id=transcript_id,
                kind=kind,
                archive_path=self._transcript_path.of(callback.get_original()),
            )
        )
