import sys
from argparse import ArgumentParser
from logging import INFO, WARNING, basicConfig, getLogger
from os import getenv
from pathlib import Path
from tempfile import gettempdir

from dotenv import load_dotenv

from src.files.work_folder.work_folder import WorkFolder
from src.flows.recordings.services import (
    ConsoleRecordingOutcome,
    LocalRecordingSource,
    RecordingLinks,
    RecordingRequest,
)
from workers.bot.recordings_factory import build_recording_run, build_storage_boundary

DEFAULT_WORK_DIR = Path(gettempdir()) / "personal_assistant" / "files"
DEFAULT_RECOGNITION_URL = "http://localhost:8000"
CHECK_CHAT_ID = 0


def require_env(name: str) -> str:
    value = getenv(name)
    if not value:
        raise ValueError(f"{name} environment variable is required")
    return value


def main() -> int:
    project_root = Path(__file__).parent.parent.parent
    load_dotenv(dotenv_path=project_root / ".env")
    basicConfig(level=INFO)
    getLogger("httpx").setLevel(WARNING)
    parser = ArgumentParser(
        description="Распознать запись тем же путём, что бот после «Да», без Telegram"
    )
    parser.add_argument("file", type=Path, help="аудиофайл записи (m4a, mp3, wav, …)")
    audio = parser.parse_args().file.resolve()
    if not audio.is_file():
        parser.error(f"{audio} — не файл")

    outcome = ConsoleRecordingOutcome(links=RecordingLinks(), write=print)
    recording_run = build_recording_run(
        downloader=LocalRecordingSource(),
        work_folder=WorkFolder(Path(getenv("PA_WORK_DIR", str(DEFAULT_WORK_DIR)))),
        storage=build_storage_boundary(Path(require_env("DROPBOX_ROOT"))),
        outcome=outcome,
        recognition_url=getenv("VOICE_RECOGNITION_URL", DEFAULT_RECOGNITION_URL),
        recognition_api_key=require_env("VOICE_RECOGNITION_API_KEY"),
    )
    recording_run.run(
        RecordingRequest(
            file_id=str(audio),
            file_name=audio.name,
            size_bytes=audio.stat().st_size,
            chat_id=CHECK_CHAT_ID,
        )
    )
    return 0 if outcome.transcript_path is not None else 1


if __name__ == "__main__":
    sys.exit(main())
