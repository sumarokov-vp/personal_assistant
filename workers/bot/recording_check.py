import sys
from argparse import ArgumentParser
from logging import INFO, WARNING, basicConfig, getLogger
from os import getenv
from pathlib import Path
from tempfile import gettempdir

from dotenv import load_dotenv
from telebot import TeleBot

from src.files.work_folder.work_folder import WorkFolder
from src.flows.recordings.services import (
    ConsoleRecordingOutcome,
    LocalRecordingSource,
    RecordingLinks,
    RecordingRequest,
)
from src.flows.recordings.services.recording_run.protocols import IRecordingOutcome
from workers.bot.fan_out_recording_outcome import FanOutRecordingOutcome
from workers.bot.recordings_factory import (
    build_recording_run,
    build_storage_boundary,
    build_telegram_outcome,
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
    return parser


def build_check_outcome(
    console: ConsoleRecordingOutcome, owner_bot: TeleBot | None
) -> IRecordingOutcome:
    if owner_bot is None:
        return console
    return FanOutRecordingOutcome(
        [console, build_telegram_outcome(owner_bot, TeleBotTextSender(owner_bot))]
    )


def main() -> int:
    project_root = Path(__file__).parent.parent.parent
    load_dotenv(dotenv_path=project_root / ".env")
    basicConfig(level=INFO)
    getLogger("httpx").setLevel(WARNING)
    parser = build_parser()
    args = parser.parse_args()
    audio = args.file.resolve()
    if not audio.is_file():
        parser.error(f"{audio} — не файл")

    console = ConsoleRecordingOutcome(links=RecordingLinks(), write=print)
    chat_id = CHECK_CHAT_ID
    owner_bot: TeleBot | None = None
    if args.notify_owner:
        chat_id = require_owner_chat_id()
        owner_bot = TeleBot(require_env("BOT_TOKEN"))
    recording_run = build_recording_run(
        downloader=LocalRecordingSource(),
        work_folder=WorkFolder(Path(getenv("PA_WORK_DIR", str(DEFAULT_WORK_DIR)))),
        storage=build_storage_boundary(Path(require_env("DROPBOX_ROOT"))),
        outcome=build_check_outcome(console, owner_bot),
        recognition_url=getenv("VOICE_RECOGNITION_URL", DEFAULT_RECOGNITION_URL),
        recognition_api_key=require_env("VOICE_RECOGNITION_API_KEY"),
    )
    recording_run.run(
        RecordingRequest(
            file_id=str(audio),
            file_name=audio.name,
            size_bytes=audio.stat().st_size,
            chat_id=chat_id,
        )
    )
    return 0 if console.transcript_path is not None else 1


if __name__ == "__main__":
    sys.exit(main())
