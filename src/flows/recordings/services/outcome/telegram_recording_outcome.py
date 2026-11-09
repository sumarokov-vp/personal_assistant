from src.flows.recordings.services.entities.protocol_callback import ProtocolCallback
from src.flows.recordings.services.entities.recorded_transcript import (
    RecordedTranscript,
)
from src.flows.recordings.services.outcome.protocols.i_buttons_sender import (
    IButtonsSender,
)
from src.flows.recordings.services.outcome.protocols.i_outcome_message_sender import (
    IOutcomeMessageSender,
)
from src.flows.recordings.services.outcome.recording_outcome_text import (
    RecordingOutcomeText,
)
from src.flows.recordings.services.recording_links.recording_links import (
    RecordingLinks,
)


class TelegramRecordingOutcome:
    def __init__(
        self,
        message_sender: IOutcomeMessageSender,
        buttons_sender: IButtonsSender,
        links: RecordingLinks,
        text: RecordingOutcomeText,
        protocol_callback: ProtocolCallback,
    ) -> None:
        self._message_sender = message_sender
        self._buttons_sender = buttons_sender
        self._links = links
        self._text = text
        self._protocol_callback = protocol_callback

    def ready(self, chat_id: int, transcript: RecordedTranscript) -> None:
        self._buttons_sender.send_with_buttons(
            chat_id=chat_id,
            text=self._text.ready(
                transcript.recording_name,
                transcript.transcript_path,
                self._links.transcript_url(transcript.transcript_path),
            ),
            buttons=self._protocol_callback.buttons(transcript.transcript_id),
        )

    def failed(self, chat_id: int, file_name: str, reason: str) -> None:
        self._message_sender.send(
            chat_id=chat_id, text=self._text.failed(file_name, reason)
        )
