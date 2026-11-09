import json
import sys
from argparse import ArgumentParser
from collections.abc import Callable
from datetime import datetime
from logging import INFO, WARNING, basicConfig, getLogger
from os import getenv
from pathlib import Path
from tempfile import gettempdir

from dotenv import load_dotenv
from telebot import TeleBot

from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.files.work_folder.work_folder import WorkFolder
from src.flows.recordings.services import (
    ConsoleRecordingOutcome,
    LocalRecordingSource,
    ProtocolCallback,
    ProtocolRequest,
    ProtocolRunResult,
    RecordedTranscript,
    RecordingLinks,
    RecordingRequest,
    RecordingTranscripts,
    TelegramProtocolChat,
)
from src.flows.recordings.services.recording_run.protocols import IRecordingOutcome
from src.flows.recordings.services.recording_run.recording_run import (
    RUSSIAN_DATE_FORMAT,
    TRANSCRIPT_MEDIA_TYPE,
    TRANSCRIPT_SOURCE,
)
from src.protocols.models.protocol_kind import ProtocolKind
from workers.bot.fan_out_recording_outcome import FanOutRecordingOutcome
from workers.bot.recordings_factory import (
    build_protocol_run,
    build_recording_run,
    build_storage_boundary,
    build_telegram_outcome,
    owner_timezone,
    protocol_model_name,
)
from workers.bot.telebot_text_sender import TeleBotTextSender

DEFAULT_WORK_DIR = Path(gettempdir()) / "personal_assistant" / "files"
DEFAULT_RECOGNITION_URL = "http://localhost:8000"
CHECK_CHAT_ID = 0


def require_env(name: str) -> str:
    value = getenv(name)
    if not value:
        raise ValueError(f"{name} environment variable is required")
    return value


def require_owner_chat_id() -> int:
    value = require_env("OWNER_TELEGRAM_ID")
    if not value.isdecimal():
        raise ValueError("OWNER_TELEGRAM_ID must be a numeric Telegram user id")
    return int(value)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Распознать запись тем же путём, что бот после «Да», без приёма из Telegram"
    )
    parser.add_argument("file", type=Path, help="аудиофайл записи (m4a, mp3, wav, …)")
    parser.add_argument(
        "--notify-owner",
        action="store_true",
        help="отправить владельцу итоговое сообщение (ссылка и кнопки протокола) "
        "тем же кодом, что после «Да»; message_id — в лог",
    )
    parser.add_argument(
        "--protocol",
        choices=[kind.value for kind in ProtocolKind],
        help="после распознавания составить протокол встречи (meeting) или звонка "
        "(call) тем же путём, что кнопка протокола: текст и PDF — владельцу, "
        ".typ и PDF — в папку записей; message_id — в вывод",
    )
    parser.add_argument(
        "--from-transcript",
        action="store_true",
        help="file — готовый JSON распознавания: сервис распознавания не зовётся, "
        "сразу протокол (нужен --protocol)",
    )
    return parser


def build_check_outcome(
    console: ConsoleRecordingOutcome, owner_bot: TeleBot | None
) -> IRecordingOutcome:
    if owner_bot is None:
        return console
    return FanOutRecordingOutcome(
        [console, build_telegram_outcome(owner_bot, TeleBotTextSender(owner_bot))]
    )


def protocol_lines(result: ProtocolRunResult) -> list[str]:
    lines = [f"protocol progress message_id {result.progress_message_id}"]
    lines.extend(
        f"protocol text message_id {message_id}"
        for message_id in result.text_message_ids
    )
    if result.pdf_message_id is not None:
        lines.append(f"protocol pdf message_id {result.pdf_message_id}")
    if result.files is not None:
        lines.append(
            f"protocol archive: {result.files.typ_path}, {result.files.pdf_path}"
        )
    if result.archive_error is not None:
        lines.append(f"protocol archive failed: {result.archive_error}")
    if result.failure is not None:
        lines.append(f"protocol failed: {result.failure}")
    return lines


def recognized(
    audio: Path,
    console: ConsoleRecordingOutcome,
    work_folder: WorkFolder,
    storage: DropboxBoundary,
    memory: RecordingTranscripts,
    chat_id: int,
    recognition_bot: TeleBot | None,
) -> RecordedTranscript | None:
    recording_run = build_recording_run(
        downloader=LocalRecordingSource(),
        work_folder=work_folder,
        storage=storage,
        outcome=build_check_outcome(console, recognition_bot),
        recognition_url=getenv("VOICE_RECOGNITION_URL", DEFAULT_RECOGNITION_URL),
        recognition_api_key=require_env("VOICE_RECOGNITION_API_KEY"),
        memory=memory,
    )
    recording_run.run(
        RecordingRequest(
            file_id=str(audio),
            file_name=audio.name,
            size_bytes=audio.stat().st_size,
            chat_id=chat_id,
        )
    )
    return console.transcript


def ready_transcript(
    transcript_json: Path, work_folder: WorkFolder, memory: RecordingTranscripts
) -> RecordedTranscript:
    content = transcript_json.read_bytes()
    work_copy = work_folder.put(
        content, transcript_json.name, TRANSCRIPT_MEDIA_TYPE, TRANSCRIPT_SOURCE
    )
    transcript = RecordedTranscript(
        transcript_id=work_copy.id,
        recording_name=transcript_json.name,
        transcript_path=transcript_json.name,
        recorded_on=datetime.now(owner_timezone()).strftime(RUSSIAN_DATE_FORMAT),
        result=json.loads(content),
    )
    memory.remember(transcript)
    return transcript


def make_protocol(
    transcript: RecordedTranscript,
    kind: ProtocolKind,
    owner_chat_id: int,
    owner_bot: TeleBot,
    work_folder: WorkFolder,
    storage: DropboxBoundary,
    memory: RecordingTranscripts,
    write: Callable[[str], None],
) -> bool:
    protocol_run = build_protocol_run(
        TelegramProtocolChat(owner_bot),
        storage,
        work_folder,
        memory,
        protocol_model_name(),
    )
    result = protocol_run.run(
        ProtocolRequest(
            chat_id=owner_chat_id,
            transcript_id=transcript.transcript_id,
            kind=kind,
            archive_path=transcript.transcript_path,
        )
    )
    for line in protocol_lines(result):
        write(line)
    return result.failure is None and result.archive_error is None


def main() -> int:
    project_root = Path(__file__).parent.parent.parent
    load_dotenv(dotenv_path=project_root / ".env")
    basicConfig(level=INFO)
    getLogger("httpx").setLevel(WARNING)
    parser = build_parser()
    args = parser.parse_args()
    source = args.file.resolve()
    if not source.is_file():
        parser.error(f"{source} — не файл")
    if args.from_transcript and args.protocol is None:
        parser.error("--from-transcript нужен вместе с --protocol")

    console = ConsoleRecordingOutcome(
        links=RecordingLinks(), protocol_callback=ProtocolCallback(), write=print
    )
    owner_bot: TeleBot | None = None
    owner_chat_id = CHECK_CHAT_ID
    if args.notify_owner or args.protocol:
        owner_chat_id = require_owner_chat_id()
        owner_bot = TeleBot(require_env("BOT_TOKEN"))
    work_folder = WorkFolder(Path(getenv("PA_WORK_DIR", str(DEFAULT_WORK_DIR))))
    storage = build_storage_boundary(Path(require_env("DROPBOX_ROOT")))
    memory = RecordingTranscripts()
    if args.from_transcript:
        transcript: RecordedTranscript | None = ready_transcript(
            source, work_folder, memory
        )
    else:
        transcript = recognized(
            source,
            console,
            work_folder,
            storage,
            memory,
            owner_chat_id if args.notify_owner else CHECK_CHAT_ID,
            owner_bot if args.notify_owner else None,
        )
    if transcript is None:
        return 1
    if args.protocol is None or owner_bot is None:
        return 0
    made = make_protocol(
        transcript,
        ProtocolKind(args.protocol),
        owner_chat_id,
        owner_bot,
        work_folder,
        storage,
        memory,
        print,
    )
    return 0 if made else 1


if __name__ == "__main__":
    sys.exit(main())
