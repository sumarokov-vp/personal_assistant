from bot_framework.core.entities.button import Button
from bot_framework.core.entities.keyboard import Keyboard
from bot_framework.core.protocols.i_message_replacer import IMessageReplacer
from bot_framework.core.protocols.i_message_sender import IMessageSender

from src.flows.recordings.card.recording_callbacks import (
    DISMISS_CALLBACK,
    RECOGNIZE_CALLBACK,
)
from src.flows.recordings.card.recording_card_text import (
    DISMISS_BUTTON_TEXT,
    RECOGNIZE_BUTTON_TEXT,
    RecordingCardText,
)


class RecordingCardPresenter:
    def __init__(
        self,
        message_sender: IMessageSender,
        message_replacer: IMessageReplacer,
        card_text: RecordingCardText,
    ) -> None:
        self._message_sender = message_sender
        self._message_replacer = message_replacer
        self._card_text = card_text

    def send_question(
        self, chat_id: int, intake_id: str, file_name: str, size_bytes: int
    ) -> None:
        self._message_sender.send(
            chat_id=chat_id,
            text=self._card_text.question(file_name, size_bytes),
            keyboard=Keyboard(
                rows=[
                    [
                        Button(
                            text=RECOGNIZE_BUTTON_TEXT,
                            callback_data=RECOGNIZE_CALLBACK.data(intake_id),
                        ),
                        Button(
                            text=DISMISS_BUTTON_TEXT,
                            callback_data=DISMISS_CALLBACK.data(intake_id),
                        ),
                    ]
                ]
            ),
        )

    def send_too_large(
        self, chat_id: int, file_name: str, size_bytes: int, max_bytes: int
    ) -> None:
        self._message_sender.send(
            chat_id=chat_id,
            text=self._card_text.too_large(file_name, size_bytes, max_bytes),
        )

    def show_recognizing(
        self, chat_id: int, message_id: int, file_name: str, size_bytes: int
    ) -> None:
        self._message_replacer.replace(
            chat_id=chat_id,
            message_id=message_id,
            text=self._card_text.recognizing(file_name, size_bytes),
        )

    def show_dismissed(
        self, chat_id: int, message_id: int, file_name: str, size_bytes: int
    ) -> None:
        self._message_replacer.replace(
            chat_id=chat_id,
            message_id=message_id,
            text=self._card_text.dismissed(file_name, size_bytes),
        )
