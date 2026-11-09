from logging import getLogger
from os import getenv
from pathlib import Path
from zoneinfo import ZoneInfo

from bot_framework.app import BotApplication
from bot_framework.platform.telegram import TelegramMessageCore
from telebot import TeleBot

from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.boundary.dropbox_folder_writer import DropboxFolderWriter
from src.files.work_folder.work_folder import WorkFolder
from src.flows.recordings import (
    DEFAULT_RECORDING_MAX_BYTES,
    DismissRecordingHandler,
    MakeProtocolHandler,
    OutcomeMessageTranscriptPath,
    PendingRecordings,
    RecognizeRecordingHandler,
    RecordingCallbackGuard,
    RecordingCardPresenter,
    RecordingCardText,
    RecordingFileDetector,
    RecordingMessageHandler,
)
from src.flows.recordings.services import (
    BackgroundProtocolMaker,
    BackgroundRecordingTranscriber,
    ProtocolCallback,
    ProtocolDrafter,
    ProtocolPrompts,
    ProtocolRun,
    ProtocolRunText,
    RecognitionFailureText,
    RecordingLinks,
    RecordingOutcomeText,
    RecordingRun,
    RecordingTranscripts,
    TelegramButtonsSender,
    TelegramProtocolChat,
    TelegramRecordingOutcome,
    TranscriptSource,
)
from src.flows.recordings.services.outcome.protocols import IOutcomeMessageSender
from src.flows.recordings.services.recording_run.protocols import (
    IRecordingDownloader,
    IRecordingOutcome,
)
from src.protocols.services.protocol_maker import ProtocolMaker
from src.protocols.services.telegram_protocol_text import TelegramProtocolText
from src.protocols.services.typst_compiler import TypstCompiler
from src.protocols.services.typst_protocol_source import TypstProtocolSource
from src.voice_recognition.repos import RecognitionJobsClient
from src.voice_recognition.services.timecoded_transcript import TimecodedTranscript
from workers.bot.protocol_model import ClaudeProtocolModel

RECORDINGS_FOLDER_VARIABLE = "RECORDINGS_FOLDER"
RECORDING_MAX_BYTES_VARIABLE = "RECORDING_MAX_BYTES"
OWNER_TIMEZONE_VARIABLE = "OWNER_TIMEZONE"
AI_MODEL_VARIABLE = "AI_MODEL"
DEFAULT_RECORDINGS_FOLDER = "Записи разговоров"
DEFAULT_OWNER_TIMEZONE = "Asia/Almaty"
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
PROTOCOL_PROMPT_FILE = "protocol_prompt.txt"
PROTOCOL_NOTES_PROMPT_FILE = "protocol_prompt_notes.txt"

logger = getLogger(__name__)


def recordings_folder() -> str:
    return getenv(RECORDINGS_FOLDER_VARIABLE) or DEFAULT_RECORDINGS_FOLDER


def recording_max_bytes() -> int:
    return int(getenv(RECORDING_MAX_BYTES_VARIABLE) or DEFAULT_RECORDING_MAX_BYTES)


def owner_timezone() -> ZoneInfo:
    return ZoneInfo(getenv(OWNER_TIMEZONE_VARIABLE) or DEFAULT_OWNER_TIMEZONE)


def protocol_model_name() -> str:
    model = getenv(AI_MODEL_VARIABLE)
    if not model:
        raise ValueError(f"{AI_MODEL_VARIABLE} environment variable is required")
    return model


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
    memory: RecordingTranscripts,
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
        memory=memory,
        timezone=owner_timezone(),
    )


def build_telegram_outcome(
    bot: TeleBot, message_sender: IOutcomeMessageSender
) -> TelegramRecordingOutcome:
    return TelegramRecordingOutcome(
        message_sender=message_sender,
        buttons_sender=TelegramButtonsSender(bot),
        links=RecordingLinks(),
        text=RecordingOutcomeText(),
        protocol_callback=ProtocolCallback(),
    )


def build_protocol_prompts(data_dir: Path = DATA_DIR) -> ProtocolPrompts:
    return ProtocolPrompts(
        protocol=(data_dir / PROTOCOL_PROMPT_FILE).read_text(encoding="utf-8"),
        notes=(data_dir / PROTOCOL_NOTES_PROMPT_FILE).read_text(encoding="utf-8"),
    )


def build_protocol_run(
    chat: TelegramProtocolChat,
    storage: DropboxBoundary,
    work_folder: WorkFolder,
    memory: RecordingTranscripts,
    model: str,
) -> ProtocolRun:
    return ProtocolRun(
        transcripts=TranscriptSource(
            memory=memory,
            work_copies=work_folder,
            archive=storage,
            timezone=owner_timezone(),
        ),
        drafter=ProtocolDrafter(
            model=ClaudeProtocolModel(model),
            prompts=build_protocol_prompts(),
            timecoded=TimecodedTranscript,
        ),
        documents=ProtocolMaker(
            source=TypstProtocolSource(),
            compiler=TypstCompiler(),
            storage=DropboxFolderWriter(boundary=storage, folder=recordings_folder()),
        ),
        text_messages=TelegramProtocolText(),
        chat=chat,
        text=ProtocolRunText(),
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
        "Recordings flow: on, folder %r, max %d bytes, protocols by model %s",
        recordings_folder(),
        recording_max_bytes(),
        protocol_model_name(),
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
    memory = RecordingTranscripts()
    outcome = build_telegram_outcome(app.core.bot, app.message_sender)
    transcriber = BackgroundRecordingTranscriber(
        recording_run=build_recording_run(
            downloader=app.core.document_downloader,
            work_folder=work_folder,
            storage=storage,
            outcome=outcome,
            recognition_url=recognition_url,
            recognition_api_key=recognition_api_key,
            memory=memory,
        ),
        failure_report=outcome,
    )
    protocol_chat = TelegramProtocolChat(app.core.bot)
    protocol_maker = BackgroundProtocolMaker(
        protocol_run=build_protocol_run(
            protocol_chat, storage, work_folder, memory, protocol_model_name()
        ),
        crash_report=protocol_chat,
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
    app.callback_handler_registry.register(
        MakeProtocolHandler(
            app.callback_answerer,
            ProtocolCallback(),
            OutcomeMessageTranscriptPath(RecordingLinks()),
            protocol_maker,
        )
    )
    app.core.message_handler_registry.register(handler=intake, content_types=["audio"])
    app.core.message_handler_registry.register(
        handler=intake,
        content_types=["document"],
        func=detector.is_recording_document,
    )
