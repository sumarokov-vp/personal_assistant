from typing import Any
from unittest.mock import MagicMock

import pytest
from bot_framework import BotMessage, BotMessageUser, Role
from bot_framework.core.entities.bot_callback import BotCallback
from bot_framework.core.entities.keyboard import Keyboard
from bot_framework.core.entities.parse_mode import ParseMode
from bot_framework.domain.role_management.repos import RoleRepo
from telebot.types import Message

from src.flows.recordings import (
    DEFAULT_RECORDING_MAX_BYTES,
    DismissRecordingHandler,
    PendingRecordings,
    RecognizeRecordingHandler,
    RecordingCallbackGuard,
    RecordingCardPresenter,
    RecordingCardText,
    RecordingFileDetector,
    RecordingMessageHandler,
)

OWNER_ID = 42
CHAT_ID = 100
CARD_MESSAGE_ID = 555
TELEGRAM_CALLBACK_DATA_LIMIT = 64
LONG_FILE_ID = (
    "BQACAgIAAxkBAAIBY2ZrZWNvcmRpbmctZmlsZS1pZC10aGF0LWlzLWxvbmdlci10aGFuLTY0LWJ5dGVz"
)


class Chat:
    def __init__(self) -> None:
        self.cards: list[tuple[str, Keyboard | None]] = []
        self.answers: list[tuple[str | None, bool]] = []

    def send(
        self,
        chat_id: int,
        text: str,
        parse_mode: ParseMode = ParseMode.HTML,
        keyboard: Keyboard | None = None,
        flow_name: str | None = None,
    ) -> BotMessage:
        self.cards.append((text, keyboard))
        return BotMessage(chat_id=chat_id, message_id=CARD_MESSAGE_ID)

    def send_media_group(
        self, chat_id: int, photo_urls: list[str], caption: str | None = None
    ) -> None:
        raise AssertionError("карточка записи не шлёт фото")

    def send_markdown_as_html(
        self,
        chat_id: int,
        text: str,
        keyboard: Keyboard | None = None,
        flow_name: str | None = None,
    ) -> BotMessage:
        return self.send(chat_id, text, keyboard=keyboard)

    def replace(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        parse_mode: ParseMode = ParseMode.HTML,
        keyboard: Keyboard | None = None,
        flow_name: str | None = None,
    ) -> BotMessage:
        assert message_id == CARD_MESSAGE_ID
        self.cards.append((text, keyboard))
        return BotMessage(chat_id=chat_id, message_id=message_id)

    def answer(
        self, callback_query_id: str, text: str | None = None, show_alert: bool = False
    ) -> None:
        self.answers.append((text, show_alert))

    def buttons(self) -> dict[str, str]:
        keyboard = self.cards[-1][1]
        if keyboard is None:
            return {}
        return {
            button.text: button.callback_data for row in keyboard.rows for button in row
        }


class IntakeKit:
    def __init__(self, max_bytes: int = DEFAULT_RECORDING_MAX_BYTES) -> None:
        self.chat = Chat()
        self.transcriber = MagicMock()
        pending = PendingRecordings()
        card = RecordingCardPresenter(self.chat, self.chat, RecordingCardText())
        role_repo = MagicMock(spec=RoleRepo)
        role_repo.get_user_roles.return_value = [Role(id=1, name="admin")]
        self.detector = RecordingFileDetector()
        self.intake = RecordingMessageHandler(
            self.detector, pending, card, self.chat, role_repo, max_bytes
        )
        guard = RecordingCallbackGuard(self.chat, pending)
        self.yes = RecognizeRecordingHandler(self.chat, guard, card, self.transcriber)
        self.no = DismissRecordingHandler(self.chat, guard, card)

    def receive(self, payload: dict[str, Any]) -> None:
        message = BotMessage(
            chat_id=CHAT_ID, message_id=1, from_user=BotMessageUser(id=OWNER_ID)
        )
        message.set_original(_telegram_message(payload))
        self.intake.handle(message)

    def press(self, data: str) -> None:
        callback = BotCallback(
            id="cb",
            user_id=OWNER_ID,
            data=data,
            message_id=CARD_MESSAGE_ID,
            message_chat_id=CHAT_ID,
        )
        handler = self.yes if data.startswith(self.yes.prefix) else self.no
        handler.handle(callback)


def _telegram_message(payload: dict[str, Any]) -> Message:
    return Message.de_json(
        {
            "message_id": 1,
            "date": 0,
            "chat": {"id": CHAT_ID, "type": "private"},
            "from": {"id": OWNER_ID, "is_bot": False, "first_name": "Owner"},
            **payload,
        }
    )


def _audio(size: int = 3 * 1024 * 1024) -> dict[str, Any]:
    return {
        "audio": {
            "file_id": LONG_FILE_ID,
            "file_unique_id": "u1",
            "duration": 600,
            "file_name": "Встреча с подрядчиком.m4a",
            "mime_type": "audio/mp4",
            "file_size": size,
        }
    }


def _document(name: str, mime_type: str, size: int = 5 * 1024 * 1024) -> dict[str, Any]:
    return {
        "document": {
            "file_id": LONG_FILE_ID,
            "file_unique_id": "u2",
            "file_name": name,
            "mime_type": mime_type,
            "file_size": size,
        }
    }


def _voice() -> dict[str, Any]:
    return {
        "voice": {
            "file_id": "voice-file",
            "file_unique_id": "u3",
            "duration": 5,
            "mime_type": "audio/ogg",
            "file_size": 20_000,
        }
    }


class TestCardOnRecording:
    def test_audio_gets_card_with_yes_and_no(self) -> None:
        kit = IntakeKit()
        kit.receive(_audio())

        text, _keyboard = kit.chat.cards[-1]
        assert "Встреча с подрядчиком.m4a" in text
        assert "3 МБ" in text
        buttons = kit.chat.buttons()
        assert set(buttons) == {"Да", "Нет"}
        assert all(
            len(data.encode()) <= TELEGRAM_CALLBACK_DATA_LIMIT
            for data in buttons.values()
        )

    @pytest.mark.parametrize(
        ("name", "mime_type"),
        [
            ("call.m4a", "audio/x-m4a"),
            ("call.m4a", "application/octet-stream"),
            ("meeting.mp3", "audio/mpeg"),
        ],
    )
    def test_audio_document_gets_card(self, name: str, mime_type: str) -> None:
        kit = IntakeKit()
        assert kit.detector.is_recording_document(
            _telegram_message(_document(name, mime_type))
        )
        kit.receive(_document(name, mime_type))

        assert set(kit.chat.buttons()) == {"Да", "Нет"}

    def test_pdf_document_is_not_recording(self) -> None:
        kit = IntakeKit()
        pdf = _document("contract.pdf", "application/pdf")
        assert not kit.detector.is_recording_document(_telegram_message(pdf))
        kit.receive(pdf)

        assert kit.chat.cards == []

    def test_voice_gets_no_card(self) -> None:
        kit = IntakeKit()
        kit.receive(_voice())

        assert kit.chat.cards == []
        kit.transcriber.transcribe.assert_not_called()


class TestAnswers:
    def test_no_dismisses_card_without_recognition(self) -> None:
        kit = IntakeKit()
        kit.receive(_audio())
        kit.press(kit.chat.buttons()["Нет"])

        text, keyboard = kit.chat.cards[-1]
        assert "не распознаю" in text
        assert keyboard is None
        kit.transcriber.transcribe.assert_not_called()

    def test_yes_calls_transcriber_once_and_repeat_does_nothing(self) -> None:
        kit = IntakeKit()
        kit.receive(_audio(size=3 * 1024 * 1024))
        yes = kit.chat.buttons()["Да"]
        kit.press(yes)
        kit.press(yes)

        kit.transcriber.transcribe.assert_called_once_with(
            file_id=LONG_FILE_ID,
            file_name="Встреча с подрядчиком.m4a",
            size_bytes=3 * 1024 * 1024,
            chat_id=CHAT_ID,
            card_message_id=CARD_MESSAGE_ID,
        )
        recognizing = [text for text, _ in kit.chat.cards if "Распознаю" in text]
        assert len(recognizing) == 1
        assert len(kit.chat.answers) == 2

    def test_no_after_yes_does_nothing(self) -> None:
        kit = IntakeKit()
        kit.receive(_audio())
        buttons = kit.chat.buttons()
        kit.press(buttons["Да"])
        kit.press(buttons["Нет"])

        assert "Распознаю" in kit.chat.cards[-1][0]
        kit.transcriber.transcribe.assert_called_once()

    def test_unknown_card_after_restart_asks_to_resend(self) -> None:
        kit = IntakeKit()
        kit.press("rec_yes:0123456789abcdef")

        kit.transcriber.transcribe.assert_not_called()
        text, show_alert = kit.chat.answers[-1]
        assert text is not None and "заново" in text
        assert show_alert


class TestSizeLimit:
    def test_oversized_recording_refused_without_buttons(self) -> None:
        kit = IntakeKit()
        kit.receive(_audio(size=31 * 1024 * 1024))

        text, keyboard = kit.chat.cards[-1]
        assert keyboard is None
        assert "31 МБ" in text
        assert "20 МБ" in text
        kit.transcriber.transcribe.assert_not_called()

    def test_limit_comes_from_constructor(self) -> None:
        kit = IntakeKit(max_bytes=1024 * 1024)
        kit.receive(_document("call.m4a", "audio/x-m4a", size=2 * 1024 * 1024))

        assert kit.chat.cards[-1][1] is None
