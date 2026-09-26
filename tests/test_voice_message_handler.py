from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from ai_framework import AIApplication, AIResponse
from bot_framework import BotMessage, BotMessageUser, Role
from bot_framework.domain.role_management.repos import RoleRepo

from src.chat.actions.send_to_agent_action import SendToAgentAction
from src.chat.actions.transcribe_voice_action import TranscribeVoiceAction
from src.chat.handlers.voice_message_handler import (
    NOTHING_HEARD_TEXT,
    TRANSCRIPTION_FAILED_TEXT,
    VoiceMessageHandler,
)
from tests.test_send_to_agent_action import (
    DatedPromptBuilder,
    ScriptedProvider,
    _ai_application,
)

CHAT_ID = 100
STATUS_MESSAGE_ID = 41
THINKING_MESSAGE_ID = 42


class StubTranscriber:
    def __init__(self, text: str | Exception) -> None:
        self.text = text
        self.seen_paths: list[Path] = []

    def __call__(self, audio_path: Path) -> str:
        self.seen_paths.append(audio_path)
        assert audio_path.read_bytes() == b"ogg-bytes"
        if isinstance(self.text, Exception):
            raise self.text
        return self.text


def _voice_message() -> BotMessage:
    message = BotMessage(chat_id=CHAT_ID, message_id=1, from_user=BotMessageUser(id=5))
    message.set_original(
        SimpleNamespace(voice=SimpleNamespace(file_id="voice-file"), audio=None)
    )
    return message


def _handler(
    ai: AIApplication, transcriber: StubTranscriber
) -> tuple[VoiceMessageHandler, MagicMock, MagicMock, MagicMock]:
    downloader = MagicMock()
    downloader.download_document.return_value = b"ogg-bytes"
    sender = MagicMock()
    sender.send.side_effect = [
        BotMessage(chat_id=CHAT_ID, message_id=STATUS_MESSAGE_ID, text="status"),
        BotMessage(chat_id=CHAT_ID, message_id=THINKING_MESSAGE_ID, text="thinking"),
    ]
    replacer = MagicMock()
    deleter = MagicMock()
    role_repo = MagicMock(spec=RoleRepo)
    role_repo.get_user_roles.return_value = [Role(id=1, name="admin")]
    handler = VoiceMessageHandler(
        transcribe_voice_action=TranscribeVoiceAction(
            document_downloader=downloader, transcriber=transcriber
        ),
        send_to_agent_action=SendToAgentAction(
            ai=ai,
            system_prompt_builder=DatedPromptBuilder(),
            message_sender=sender,
            message_replacer=replacer,
            message_deleter=deleter,
        ),
        message_sender=sender,
        message_replacer=replacer,
        message_deleter=deleter,
        role_repo=role_repo,
    )
    return handler, sender, replacer, deleter


class TestVoiceThroughAIApplication:
    def test_transcript_goes_to_assistant_and_reply_lands_in_chat(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = ScriptedProvider([AIResponse(content="Добавил хлеб в покупки")])
        transcriber = StubTranscriber("  Купи хлеб  ")
        with _ai_application(monkeypatch, provider) as ai:
            handler, sender, replacer, deleter = _handler(ai, transcriber)
            handler.handle(_voice_message())

        messages, _system = provider.calls[0]
        assert [(m.role, m.content) for m in messages] == [("user", "Купи хлеб")]
        deleter.delete.assert_called_once_with(
            chat_id=CHAT_ID, message_id=STATUS_MESSAGE_ID
        )
        replacer.replace.assert_called_once_with(
            chat_id=CHAT_ID,
            message_id=THINKING_MESSAGE_ID,
            text="Добавил хлеб в покупки",
        )
        sender.send_document.assert_not_called()
        assert not transcriber.seen_paths[0].exists()

    def test_empty_transcript_does_not_reach_assistant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = ScriptedProvider([])
        with _ai_application(monkeypatch, provider) as ai:
            handler, sender, _replacer, deleter = _handler(ai, StubTranscriber("   "))
            handler.handle(_voice_message())

        assert provider.calls == []
        deleter.delete.assert_called_once_with(
            chat_id=CHAT_ID, message_id=STATUS_MESSAGE_ID
        )
        sender.send.assert_called_with(chat_id=CHAT_ID, text=NOTHING_HEARD_TEXT)

    def test_transcription_failure_reported_and_audio_removed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = ScriptedProvider([])
        transcriber = StubTranscriber(RuntimeError("whisper down"))
        with _ai_application(monkeypatch, provider) as ai:
            handler, _sender, replacer, _deleter = _handler(ai, transcriber)
            handler.handle(_voice_message())

        assert provider.calls == []
        replacer.replace.assert_called_once_with(
            chat_id=CHAT_ID,
            message_id=STATUS_MESSAGE_ID,
            text=TRANSCRIPTION_FAILED_TEXT,
        )
        assert not transcriber.seen_paths[0].exists()
