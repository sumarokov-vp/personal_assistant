import json
import threading
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any
from unittest.mock import MagicMock
from urllib.parse import parse_qs, unquote, urlsplit

import httpx
from bot_framework import BotMessage, BotMessageUser, Role
from bot_framework.core.entities.bot_callback import BotCallback
from bot_framework.core.entities.keyboard import Keyboard
from bot_framework.core.entities.parse_mode import ParseMode
from bot_framework.domain.role_management.repos import RoleRepo
from telebot.types import Message

from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.files.work_folder.work_folder import WorkFolder
from src.flows.recordings import (
    DEFAULT_RECORDING_MAX_BYTES,
    PendingRecordings,
    RecognizeRecordingHandler,
    RecordingCallbackGuard,
    RecordingCardPresenter,
    RecordingCardText,
    RecordingFileDetector,
    RecordingMessageHandler,
)
from src.flows.recordings.services import (
    THREAD_NAME_PREFIX,
    BackgroundRecordingTranscriber,
    CallbackButton,
    ProtocolCallback,
    RecognitionFailureText,
    RecordingLinks,
    RecordingOutcomeText,
    RecordingRun,
    RecordingTranscripts,
    TelegramRecordingOutcome,
)
from src.voice_recognition.repos import RecognitionJobsClient

OWNER_ID = 42
CHAT_ID = 100
CARD_MESSAGE_ID = 555
FILE_ID = "telegram-file-id"
RECORDING_NAME = "Встреча с подрядчиком.m4a"
RECORDINGS_FOLDER = "Записи разговоров"
WORK_FILE_METADATA = ".work_file.json"
AUDIO = b"fake m4a bytes"
JOB_ID = "job-1"
SERVICE_URL = "http://recognition.test"
RESULT: dict[str, Any] = {
    "text": "Добрый день. Обсудим сроки.",
    "language": "ru",
    "segments": [
        {"start": 0.0, "end": 1.5, "text": "Добрый день."},
        {"start": 1.5, "end": 3.0, "text": "Обсудим сроки."},
    ],
}


class Chat:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.keyboards: list[Keyboard] = []
        self.with_buttons: list[tuple[str, list[CallbackButton]]] = []

    def send(
        self,
        chat_id: int,
        text: str,
        parse_mode: ParseMode = ParseMode.HTML,
        keyboard: Keyboard | None = None,
        flow_name: str | None = None,
    ) -> BotMessage:
        self.sent.append(text)
        if keyboard is not None:
            self.keyboards.append(keyboard)
        return BotMessage(chat_id=chat_id, message_id=CARD_MESSAGE_ID)

    def send_media_group(
        self, chat_id: int, photo_urls: list[str], caption: str | None = None
    ) -> None:
        raise AssertionError("поток записи не шлёт фото")

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
        return BotMessage(chat_id=chat_id, message_id=message_id)

    def answer(
        self, callback_query_id: str, text: str | None = None, show_alert: bool = False
    ) -> None:
        return None

    def send_with_buttons(
        self, chat_id: int, text: str, buttons: list[CallbackButton]
    ) -> None:
        self.with_buttons.append((text, buttons))


class Telegram:
    def download_document(self, file_id: str) -> bytes:
        assert file_id == FILE_ID
        return AUDIO


class RecognitionService:
    def __init__(self, final_job: dict[str, Any] | None, healthy: bool = True) -> None:
        self._final_job = final_job
        self._healthy = healthy
        self.uploaded: list[bytes] = []
        self.polls = 0

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        if not self._healthy:
            raise httpx.ConnectError("станция выключена", request=request)
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.method == "POST":
            self.uploaded.append(request.read())
            return httpx.Response(202, json={"job_id": JOB_ID, "status": "pending"})
        self.polls += 1
        if self.polls == 1:
            return httpx.Response(200, json={"job_id": JOB_ID, "status": "processing"})
        return httpx.Response(200, json=self._final_job)


class RecordingKit:
    def __init__(self, tmp_path: Path, service: RecognitionService) -> None:
        self.chat = Chat()
        self.work_dir = tmp_path / "work"
        self.storage_root = tmp_path / "Dropbox"
        self.storage_root.mkdir()
        self.service = service
        outcome = TelegramRecordingOutcome(
            message_sender=self.chat,
            buttons_sender=self.chat,
            links=RecordingLinks(),
            text=RecordingOutcomeText(),
            protocol_callback=ProtocolCallback(),
        )
        self.memory = RecordingTranscripts()
        recording_run = RecordingRun(
            downloader=Telegram(),
            work_folder=WorkFolder(self.work_dir),
            recognition=RecognitionJobsClient(
                base_url=SERVICE_URL,
                api_key="key",
                transport=service.transport(),
                sleep=lambda _seconds: None,
            ),
            transcripts=DropboxBoundary(self.storage_root, DropboxAccessPolicy()),
            outcome=outcome,
            failure_text=RecognitionFailureText(),
            transcripts_folder=RECORDINGS_FOLDER,
            memory=self.memory,
            timezone=ZoneInfo("Asia/Almaty"),
        )
        transcriber = BackgroundRecordingTranscriber(recording_run, outcome)
        pending = PendingRecordings()
        card = RecordingCardPresenter(self.chat, self.chat, RecordingCardText())
        role_repo = MagicMock(spec=RoleRepo)
        role_repo.get_user_roles.return_value = [Role(id=1, name="admin")]
        self._intake = RecordingMessageHandler(
            RecordingFileDetector(),
            pending,
            card,
            self.chat,
            role_repo,
            DEFAULT_RECORDING_MAX_BYTES,
        )
        self._yes = RecognizeRecordingHandler(
            self.chat, RecordingCallbackGuard(self.chat, pending), card, transcriber
        )

    def forward_recording_and_press_yes(self) -> None:
        message = BotMessage(
            chat_id=CHAT_ID, message_id=1, from_user=BotMessageUser(id=OWNER_ID)
        )
        message.set_original(_audio_message())
        self._intake.handle(message)
        self._yes.handle(
            BotCallback(
                id="cb",
                user_id=OWNER_ID,
                data=self._yes_callback_data(),
                message_id=CARD_MESSAGE_ID,
                message_chat_id=CHAT_ID,
            )
        )
        _wait_for_recording_threads()

    def audio_left_in_work_folder(self) -> list[Path]:
        return [path for path in self.work_dir.rglob("*.m4a") if path.is_file()]

    def transcript_work_copies(self) -> list[Path]:
        return sorted(
            path
            for path in self.work_dir.rglob("*.json")
            if path.name != WORK_FILE_METADATA
        )

    def transcripts(self) -> list[Path]:
        folder = self.storage_root / RECORDINGS_FOLDER
        return sorted(folder.iterdir()) if folder.exists() else []

    def _yes_callback_data(self) -> str:
        [yes] = [
            button.callback_data
            for row in self.chat.keyboards[-1].rows
            for button in row
            if button.text == "Да"
        ]
        return yes


def _audio_message() -> Message:
    return Message.de_json(
        {
            "message_id": 1,
            "date": 0,
            "chat": {"id": CHAT_ID, "type": "private"},
            "from": {"id": OWNER_ID, "is_bot": False, "first_name": "Owner"},
            "audio": {
                "file_id": FILE_ID,
                "file_unique_id": "u1",
                "duration": 600,
                "file_name": RECORDING_NAME,
                "mime_type": "audio/mp4",
                "file_size": len(AUDIO),
            },
        }
    )


def _wait_for_recording_threads() -> None:
    for thread in threading.enumerate():
        if thread.name.startswith(THREAD_NAME_PREFIX):
            thread.join(timeout=5)
            assert not thread.is_alive()


def _completed() -> dict[str, Any]:
    return {"job_id": JOB_ID, "status": "completed", "result": RESULT}


def _failed() -> dict[str, Any]:
    return {"job_id": JOB_ID, "status": "failed", "error": "CUDA out of memory"}


class TestRecognizedRecording:
    def test_transcript_lands_in_recordings_folder_and_audio_is_removed(
        self, tmp_path: Path
    ) -> None:
        kit = RecordingKit(tmp_path, RecognitionService(_completed()))
        kit.forward_recording_and_press_yes()

        assert kit.service.uploaded and AUDIO in kit.service.uploaded[0]
        [transcript] = kit.transcripts()
        assert transcript.name == "Встреча с подрядчиком.json"
        assert json.loads(transcript.read_text(encoding="utf-8")) == RESULT
        assert kit.audio_left_in_work_folder() == []
        [work_copy] = kit.transcript_work_copies()
        assert json.loads(work_copy.read_text(encoding="utf-8")) == RESULT
        remembered = kit.memory.recall(work_copy.parent.name)
        assert remembered is not None
        assert remembered.result == RESULT

    def test_owner_gets_link_and_two_protocol_callback_buttons(
        self, tmp_path: Path
    ) -> None:
        kit = RecordingKit(tmp_path, RecognitionService(_completed()))
        kit.forward_recording_and_press_yes()

        [(text, buttons)] = kit.chat.with_buttons
        transcript_path = f"{RECORDINGS_FOLDER}/Встреча с подрядчиком.json"
        link = urlsplit(text.split('href="')[1].split('"')[0].replace("&amp;", "&"))
        assert link.netloc == "www.dropbox.com"
        assert unquote(link.path) == f"/home/{RECORDINGS_FOLDER}"
        assert parse_qs(link.query)["preview"] == ["Встреча с подрядчиком.json"]
        assert [button.text for button in buttons] == [
            "Протокол встречи",
            "Протокол звонка",
        ]
        [work_copy] = kit.transcript_work_copies()
        transcript_id = work_copy.parent.name
        assert [button.data for button in buttons] == [
            f"prt:m:{transcript_id}",
            f"prt:c:{transcript_id}",
        ]
        assert all(len(button.data.encode()) <= 64 for button in buttons)
        assert transcript_path in text
        assert "claude.ai" not in text

    def test_repeated_name_gets_numbered_transcript(self, tmp_path: Path) -> None:
        kit = RecordingKit(tmp_path, RecognitionService(_completed()))
        existing = kit.storage_root / RECORDINGS_FOLDER
        existing.mkdir()
        (existing / "Встреча с подрядчиком.json").write_text("{}")

        kit.forward_recording_and_press_yes()

        assert [path.name for path in kit.transcripts()] == [
            "Встреча с подрядчиком (2).json",
            "Встреча с подрядчиком.json",
        ]
        assert "Встреча с подрядчиком (2).json" in kit.chat.with_buttons[0][0]


class TestFailedRecognition:
    def test_failed_job_reports_error_without_transcript(self, tmp_path: Path) -> None:
        kit = RecordingKit(tmp_path, RecognitionService(_failed()))
        kit.forward_recording_and_press_yes()

        assert kit.transcripts() == []
        assert kit.audio_left_in_work_folder() == []
        assert kit.transcript_work_copies() == []
        assert kit.chat.with_buttons == []
        assert "не распознана" in kit.chat.sent[-1]
        assert "CUDA out of memory" in kit.chat.sent[-1]
        assert "Перешлите её позже" in kit.chat.sent[-1]

    def test_unavailable_service_reports_error_without_transcript(
        self, tmp_path: Path
    ) -> None:
        kit = RecordingKit(tmp_path, RecognitionService(None, healthy=False))
        kit.forward_recording_and_press_yes()

        assert kit.transcripts() == []
        assert kit.audio_left_in_work_folder() == []
        assert kit.transcript_work_copies() == []
        assert kit.chat.with_buttons == []
        assert "сервис распознавания недоступен" in kit.chat.sent[-1]
        assert "Перешлите её позже" in kit.chat.sent[-1]
