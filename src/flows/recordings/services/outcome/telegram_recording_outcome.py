from src.flows.recordings.services.entities.url_button import UrlButton
from src.flows.recordings.services.outcome.protocols.i_outcome_message_sender import (
    IOutcomeMessageSender,
)
from src.flows.recordings.services.outcome.protocols.i_url_buttons_sender import (
    IUrlButtonsSender,
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
        url_buttons_sender: IUrlButtonsSender,
        links: RecordingLinks,
        text: RecordingOutcomeText,
    ) -> None:
        self._message_sender = message_sender
        self._url_buttons_sender = url_buttons_sender
        self._links = links
        self._text = text

    def ready(self, chat_id: int, file_name: str, transcript_path: str) -> None:
        prompts = self._links.protocol_prompts(transcript_path)
        self._url_buttons_sender.send_with_url_buttons(
            chat_id=chat_id,
            text=self._text.ready(
                file_name,
                transcript_path,
                self._links.transcript_url(transcript_path),
                prompts,
            ),
            buttons=[
                UrlButton(text=prompt.title, url=prompt.url) for prompt in prompts
            ],
        )

    def failed(self, chat_id: int, file_name: str, reason: str) -> None:
        self._message_sender.send(
            chat_id=chat_id, text=self._text.failed(file_name, reason)
        )
