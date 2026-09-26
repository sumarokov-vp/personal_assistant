from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from ai_framework import AIApplication, AIResponse
from bot_framework import BotMessage, BotMessageUser

from src.chat.handlers.photo_message_handler import PhotoMessageHandler
from tests.chat.manual_timer_factory import ManualTimerFactory
from tests.test_attachment_handlers import (
    CHAT_ID,
    MAX_FILE_BYTES,
    MAX_IMAGE_BYTES,
    THINKING_MESSAGE_ID,
    USER_ID,
    _action,
    _admin_role_repo,
    _ai_application,
    _collaborators,
)
from tests.test_send_to_agent_action import ScriptedProvider

FIRST_JPEG = b"\xff\xd8 first"
SECOND_JPEG = b"\xff\xd8 second"


def _album_photo(message_id: int, file_id: str, caption: str | None) -> BotMessage:
    message = BotMessage(
        chat_id=CHAT_ID, message_id=message_id, from_user=BotMessageUser(id=USER_ID)
    )
    message.set_original(
        SimpleNamespace(
            photo=[SimpleNamespace(file_id=file_id, file_size=100)],
            caption=caption,
            media_group_id="album-1",
        )
    )
    return message


def _handler(
    ai: AIApplication, mocks: dict[str, MagicMock], timers: ManualTimerFactory
) -> PhotoMessageHandler:
    return PhotoMessageHandler(
        document_downloader=mocks["downloader"],
        send_to_agent_action=_action(ai, mocks),
        message_sender=mocks["sender"],
        message_replacer=mocks["replacer"],
        role_repo=_admin_role_repo(),
        max_file_bytes=MAX_FILE_BYTES,
        max_image_bytes=MAX_IMAGE_BYTES,
        timer_factory=timers,
    )


def _mocks_downloading(files: dict[str, bytes]) -> dict[str, MagicMock]:
    mocks = _collaborators(b"")
    mocks["downloader"].download_document.side_effect = files.__getitem__
    return mocks


class TestPhotoAlbum:
    def test_album_goes_to_assistant_as_one_request_after_quiet_period(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = ScriptedProvider([AIResponse(content="Две джерси")])
        mocks = _mocks_downloading({"f1": FIRST_JPEG, "f2": SECOND_JPEG})
        timers = ManualTimerFactory()
        with _ai_application(monkeypatch, provider) as ai:
            handler = _handler(ai, mocks, timers)
            handler.handle(_album_photo(11, "f2", caption="Согласованный дизайн"))
            handler.handle(_album_photo(10, "f1", caption=None))

            assert provider.calls == []
            mocks["sender"].send.assert_not_called()

            timers.timers[-1].fire()

        assert len(provider.calls) == 1
        messages, _system = provider.calls[0]
        sent = messages[-1]
        assert sent.content == "Согласованный дизайн"
        assert sent.attachments is not None
        assert [a.data for a in sent.attachments] == [FIRST_JPEG, SECOND_JPEG]
        mocks["sender"].send.assert_called_once_with(chat_id=CHAT_ID, text="Думаю...")
        mocks["replacer"].replace.assert_called_once_with(
            chat_id=CHAT_ID, message_id=THINKING_MESSAGE_ID, text="Две джерси"
        )

    def test_superseded_timer_of_album_does_not_send(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = ScriptedProvider([AIResponse(content="Готово")])
        mocks = _mocks_downloading({"f1": FIRST_JPEG, "f2": SECOND_JPEG})
        timers = ManualTimerFactory()
        with _ai_application(monkeypatch, provider) as ai:
            handler = _handler(ai, mocks, timers)
            handler.handle(_album_photo(10, "f1", caption=None))
            handler.handle(_album_photo(11, "f2", caption=None))
            first_timer, last_timer = timers.timers

            first_timer.fire()
            assert provider.calls == []

            last_timer.fire()

        assert first_timer.cancelled
        assert len(provider.calls) == 1
