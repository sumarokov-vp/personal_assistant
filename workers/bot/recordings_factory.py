from logging import getLogger
from os import getenv
from pathlib import Path

from bot_framework.app import BotApplication
from bot_framework.platform.telegram import TelegramMessageCore

from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.files.work_folder.work_folder import WorkFolder
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
from src.flows.recordings.services import (
    BackgroundRecordingTranscriber,
    RecognitionFailureText,
    RecordingLinks,
    RecordingOutcomeText,
    RecordingRun,
    TelegramRecordingOutcome,
    TelegramUrlButtonsSender,
)
from src.flows.recordings.services.recording_run.protocols import (
    IRecordingDownloader,
    IRecordingOutcome,
)
from src.voice_recognition.repos import RecognitionJobsClient

RECORDINGS_FOLDER_VARIABLE = "RECORDINGS_FOLDER"
RECORDING_MAX_BYTES_VARIABLE = "RECORDING_MAX_BYTES"
DEFAULT_RECORDINGS_FOLDER = "Записи разговоров"

logger = getLogger(__name__)


def recordings_folder() -> str:
    return getenv(RECORDINGS_FOLDER_VARIABLE) or DEFAULT_RECORDINGS_FOLDER


def recording_max_bytes() -> int:
    return int(getenv(RECORDING_MAX_BYTES_VARIABLE) or DEFAULT_RECORDING_MAX_BYTES)


def build_storage_boundary(root: Path) -> DropboxBoundary:
    if not root.is_dir():
        raise ValueError(f"DROPBOX_ROOT={root} is not a directory")
    return DropboxBoundary(root=root, policy=DropboxAccessPolicy())


def build_recording_run(
    downloader: IRecordingDownloader,
    work_folder: WorkFolder,
    storage: DropboxBoundary,
    outcome: IRecordingOutcome,
    recognition_url: str,
    recognition_api_key: str,
) -> RecordingRun:
    return RecordingRun(
        downloader=downloader,
        work_folder=work_folder,
        recognition=RecognitionJobsClient(
            base_url=recognition_url, api_key=recognition_api_key
        ),
        transcripts=storage,
        outcome=outcome,
        failure_text=RecognitionFailureText(),
        transcripts_folder=recordings_folder(),
    )


def register_configured_recording_flow(
    app: BotApplication,
    storage: DropboxBoundary | None,
    work_folder: WorkFolder,
    recognition_url: str,
    recognition_api_key: str | None,
) -> bool:
    if storage is None or not recognition_api_key:
        logger.info(
            "Recordings flow: off (needs DROPBOX_ROOT and VOICE_RECOGNITION_API_KEY)"
        )
        return False
    register_recording_flow(
        app, storage, work_folder, recognition_url, recognition_api_key
    )
    logger.info(
        "Recordings flow: on, folder %r, max %d bytes",
        recordings_folder(),
        recording_max_bytes(),
    )
    return True


def register_recording_flow(
    app: BotApplication,
    storage: DropboxBoundary,
    work_folder: WorkFolder,
    recognition_url: str,
    recognition_api_key: str,
) -> None:
    if not isinstance(app.core, TelegramMessageCore):
        raise TypeError("Recordings flow requires TelegramMessageCore")
    outcome = TelegramRecordingOutcome(
        message_sender=app.message_sender,
        url_buttons_sender=TelegramUrlButtonsSender(app.core.bot),
        links=RecordingLinks(),
        text=RecordingOutcomeText(),
    )
    transcriber = BackgroundRecordingTranscriber(
        recording_run=build_recording_run(
            downloader=app.core.document_downloader,
            work_folder=work_folder,
            storage=storage,
            outcome=outcome,
            recognition_url=recognition_url,
            recognition_api_key=recognition_api_key,
        ),
        failure_report=outcome,
    )
    pending = PendingRecordings()
    detector = RecordingFileDetector()
    card = RecordingCardPresenter(
        app.message_sender, app.message_replacer, RecordingCardText()
    )
    guard = RecordingCallbackGuard(app.callback_answerer, pending)
    intake = RecordingMessageHandler(
        detector,
        pending,
        card,
        app.message_sender,
        app.role_repo,
        recording_max_bytes(),
    )
    app.callback_handler_registry.register(
        RecognizeRecordingHandler(app.callback_answerer, guard, card, transcriber)
    )
    app.callback_handler_registry.register(
        DismissRecordingHandler(app.callback_answerer, guard, card)
    )
    app.core.message_handler_registry.register(handler=intake, content_types=["audio"])
    app.core.message_handler_registry.register(
        handler=intake,
        content_types=["document"],
        func=detector.is_recording_document,
    )
