from logging import WARNING, basicConfig, getLogger
from os import getenv
from pathlib import Path
from tempfile import gettempdir
from threading import Thread
from time import sleep
from zoneinfo import ZoneInfo

import httpx
from ai_framework import AIApplication, BaseTool, Provider
from ai_framework.attachments.s3_attachment_store import S3AttachmentStore
from ai_framework.memory.postgres_memory_store import PostgresMemoryStore
from bot_framework.app import BotApplication
from bot_framework.platform.telegram import TelegramMessageCore
from dotenv import load_dotenv

from src.access.services.owner_gate import OwnerUpdateGate
from src.access.services.update_gate_installer import UpdateGateInstaller
from src.ai_tools import (
    MemoryCloseCommitmentTool,
    MemoryShowTool,
    MemoryUpsertCommitmentTool,
    MemoryUpsertDeadlineTool,
    MemoryUpsertTripTool,
    WikiAppendTool,
    WikiCreatePageTool,
    WikiReadTool,
    WikiSearchTool,
)
from src.ai_tools.dropbox_propose_moves import DropboxProposeMovesTool
from src.ai_tools.dropbox_read import DropboxReadTool
from src.ai_tools.dropbox_save import DropboxSaveTool
from src.ai_tools.dropbox_search import DropboxSearchTool
from src.ai_tools.dropbox_tree import DropboxTreeTool
from src.ai_tools.dropbox_undo_moves import DropboxUndoMovesTool
from src.app_migrations import apply_migrations
from src.chat.actions.send_to_agent_action import SendToAgentAction
from src.chat.actions.system_prompt_builder import SystemPromptBuilder
from src.chat.actions.transcribe_voice_action import TranscribeVoiceAction
from src.chat.handlers.clear_command_handler import ClearCommandHandler
from src.chat.handlers.document_message_handler import DocumentMessageHandler
from src.chat.handlers.photo_message_handler import PhotoMessageHandler
from src.chat.handlers.text_message_handler import TextMessageHandler
from src.chat.handlers.voice_message_handler import VoiceMessageHandler
from src.dropbox.repos.postgres_dropbox_journal_repository import (
    PostgresDropboxJournalRepository,
)
from src.dropbox.repos.postgres_move_plan_repository import PostgresMovePlanRepository
from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.move_canceller.move_plan_canceller import MovePlanCanceller
from src.dropbox.services.move_executor.move_plan_executor import MovePlanExecutor
from src.dropbox.services.move_planner.move_planner import MovePlanner
from src.dropbox.services.move_rollback.move_plan_rollback import MovePlanRollback
from src.dropbox.services.move_validator.move_plan_validator import MovePlanValidator
from src.dropbox.services.reader.dropbox_reader import DropboxReader
from src.dropbox.services.saver.dropbox_file_saver import DropboxFileSaver
from src.dropbox.services.search.dropbox_search import DropboxSearch
from src.dropbox.services.tree.dropbox_tree import DropboxTree
from src.files.overflow.overflow_folder import OVERFLOW_FOLDER_NAME
from src.files.readers.file_text_reader import FileTextReader
from src.files.sources.chat_attachments.chat_attachments import ChatAttachments
from src.files.sweeper.sweeper import Sweeper
from src.files.work_folder.work_folder import WorkFolder
from src.flows.dropbox_moves import (
    CancelMovePlanHandler,
    ExecuteMovePlanHandler,
    MovePlanCallbackGuard,
    MovePlanCardPresenter,
    MovePlanCardText,
    RollbackMovePlanHandler,
)
from src.memory.repos import (
    CommitmentRepository,
    DeadlineRepository,
    WhereaboutsRepository,
    WikiPageStorage,
)
from src.wiki import WikiFactory, WikiPageNotFoundError, WikiSettings
from src.wiki.search import WikiSearcher
from src.gmail.repos.gmail_client import GmailClient
from workers.bot.file_tools_factory import build_file_tools
from workers.bot.gmail_tools_factory import (
    GMAIL_VARIABLES,
    build_gmail_client,
    build_gmail_tools,
)
from workers.bot.todoist_tools_factory import build_todoist_tools
from workers.bot.transcriber_factory import build_transcriber

logger = getLogger(__name__)

TOKEN_LEAKING_LOGGERS = ["TeleBot", "urllib3", "requests", "httpx", "anthropic"]

HISTORY_TURNS_LIMIT = 10
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
# Лимит Claude на одну картинку (в base64): больше — отказ без вызова модели
MAX_IMAGE_BYTES = 5 * 1024 * 1024
CARD_LANGUAGE = "ru"
SUBSCRIPTION_HAS_NO_API_KEY = ""
GMAIL_HTTP_TIMEOUT_SECONDS = 30.0
DEFAULT_WORK_DIR = Path(gettempdir()) / "personal_assistant" / "files"
SWEEP_INTERVAL_SECONDS = 60 * 60


def configure_logging(level: str) -> None:
    basicConfig(level=level.upper())
    for name in TOKEN_LEAKING_LOGGERS:
        getLogger(name).setLevel(WARNING)


def require_env(name: str) -> str:
    value = getenv(name)
    if not value:
        raise ValueError(f"{name} environment variable is required")
    return value


def require_owner_telegram_id() -> int:
    value = require_env("OWNER_TELEGRAM_ID")
    if not value.isdecimal():
        raise ValueError("OWNER_TELEGRAM_ID must be a numeric Telegram user id")
    return int(value)


def admit_only_owner(app: BotApplication, owner_telegram_id: int) -> None:
    if not isinstance(app.core, TelegramMessageCore):
        raise TypeError("Owner gate requires TelegramMessageCore")
    UpdateGateInstaller(OwnerUpdateGate(owner_telegram_id)).install(app.core.bot)


def build_dropbox_boundary(root: Path) -> DropboxBoundary:
    if not root.is_dir():
        raise ValueError(f"DROPBOX_ROOT={root} is not a directory")
    return DropboxBoundary(root=root, policy=DropboxAccessPolicy())


def build_dropbox_tools(
    boundary: DropboxBoundary, text_reader: FileTextReader
) -> list[BaseTool]:
    return [
        DropboxTreeTool(tree_builder=DropboxTree(boundary=boundary)),
        DropboxSearchTool(finder=DropboxSearch(boundary=boundary)),
        DropboxReadTool(
            reader=DropboxReader(boundary=boundary, text_reader=text_reader)
        ),
    ]


def build_dropbox_move_tools(
    boundary: DropboxBoundary, database_url: str, app: BotApplication
) -> list[BaseTool]:
    apply_migrations(database_url)
    plans = PostgresMovePlanRepository(database_url=database_url)
    journal = PostgresDropboxJournalRepository(database_url=database_url)
    validator = MovePlanValidator(boundary=boundary)
    card = MovePlanCardPresenter(
        message_sender=app.message_sender,
        message_replacer=app.message_replacer,
        card_text=MovePlanCardText(
            phrase_repo=app.phrase_repo, language_code=CARD_LANGUAGE
        ),
        phrase_repo=app.phrase_repo,
        language_code=CARD_LANGUAGE,
    )
    guard = MovePlanCallbackGuard(
        callback_answerer=app.callback_answerer,
        plans=plans,
        phrase_repo=app.phrase_repo,
        language_code=CARD_LANGUAGE,
    )
    for handler in (
        ExecuteMovePlanHandler(
            callback_answerer=app.callback_answerer,
            guard=guard,
            executor=MovePlanExecutor(
                plans=plans, validator=validator, boundary=boundary, journal=journal
            ),
            card=card,
        ),
        CancelMovePlanHandler(
            callback_answerer=app.callback_answerer,
            guard=guard,
            canceller=MovePlanCanceller(plans=plans),
            card=card,
        ),
        RollbackMovePlanHandler(
            callback_answerer=app.callback_answerer,
            guard=guard,
            rollback=MovePlanRollback(plans=plans, boundary=boundary, journal=journal),
            card=card,
        ),
    ):
        app.callback_handler_registry.register(handler)
    return [
        DropboxProposeMovesTool(
            proposer=MovePlanner(validator=validator, plans=plans), card_sender=card
        ),
        DropboxUndoMovesTool(plans=plans, offer_sender=card),
    ]


def build_chat_attachments(
    ai_database_url: str, attachment_store: S3AttachmentStore
) -> ChatAttachments:
    return ChatAttachments(
        history=PostgresMemoryStore(ai_database_url),
        store=attachment_store,
        turns_limit=HISTORY_TURNS_LIMIT,
    )


def build_dropbox_save_tool(
    boundary: DropboxBoundary, database_url: str, work_folder: WorkFolder
) -> BaseTool:
    return DropboxSaveTool(
        work_files=work_folder,
        saver=DropboxFileSaver(
            boundary=boundary,
            journal=PostgresDropboxJournalRepository(database_url=database_url),
        ),
    )


def sweep_forever(sweeper: Sweeper) -> None:
    while True:
        try:
            for path in sweeper.sweep():
                logger.info("Sweeper removed %s", path)
        except OSError:
            logger.exception("Sweeper pass failed")
        sleep(SWEEP_INTERVAL_SECONDS)


def start_sweeper(work_dir: Path, dropbox_root: str | None) -> None:
    roots = [work_dir]
    if dropbox_root:
        roots.append(Path(dropbox_root) / OVERFLOW_FOLDER_NAME)
    Thread(
        target=sweep_forever, args=(Sweeper(roots),), name="files-sweeper", daemon=True
    ).start()


def build_wiki_factory() -> WikiFactory:
    ssh_key_path = getenv("WIKI_SSH_KEY_PATH")
    return WikiFactory(
        WikiSettings(
            wiki_dir=Path(require_env("WIKI_DIR")),
            remote_url=require_env("WIKI_REMOTE_URL"),
            ssh_key_path=Path(ssh_key_path) if ssh_key_path else None,
        )
    )


def build_attachment_store() -> S3AttachmentStore:
    # AIApplication сам оборачивает хранилище в CachedAttachmentStore (LRU в памяти процесса)
    return S3AttachmentStore(
        endpoint_url=require_env("ATTACHMENTS_S3_ENDPOINT"),
        bucket=require_env("ATTACHMENTS_S3_BUCKET"),
        access_key=require_env("ATTACHMENTS_S3_ACCESS_KEY"),
        secret_key=require_env("ATTACHMENTS_S3_SECRET_KEY"),
        region=require_env("ATTACHMENTS_S3_REGION"),
    )


def build_wiki_tools(wiki_factory: WikiFactory) -> list[BaseTool]:
    reader = wiki_factory.create_reader()
    writer = wiki_factory.create_writer()
    return [
        WikiSearchTool(searcher=WikiSearcher(reader)),
        WikiReadTool(reader=reader),
        WikiCreatePageTool(creator=writer, lister=reader),
        WikiAppendTool(appender=writer),
    ]


def build_memory_tools(wiki_factory: WikiFactory, timezone: ZoneInfo) -> list[BaseTool]:
    storage = WikiPageStorage(
        reader=wiki_factory.create_reader(),
        writer=wiki_factory.create_writer(),
        page_not_found_error=WikiPageNotFoundError,
    )
    deadlines = DeadlineRepository(storage)
    whereabouts = WhereaboutsRepository(storage)
    commitments = CommitmentRepository(storage)
    return [
        MemoryShowTool(
            deadlines=deadlines, whereabouts=whereabouts, commitments=commitments
        ),
        MemoryUpsertDeadlineTool(deadlines=deadlines, timezone=timezone),
        MemoryUpsertTripTool(whereabouts=whereabouts),
        MemoryUpsertCommitmentTool(commitments=commitments),
        MemoryCloseCommitmentTool(commitments=commitments),
    ]


def gmail_configured() -> bool:
    return any(getenv(name) for name in GMAIL_VARIABLES)


def build_configured_gmail_client() -> GmailClient | None:
    if not gmail_configured():
        return None
    return build_gmail_client(
        http=httpx.Client(timeout=GMAIL_HTTP_TIMEOUT_SECONDS),
        client_id=require_env("GMAIL_CLIENT_ID"),
        client_secret=require_env("GMAIL_CLIENT_SECRET"),
        refresh_token=require_env("GMAIL_REFRESH_TOKEN"),
    )


def main() -> None:
    project_root = Path(__file__).parent.parent.parent
    load_dotenv(dotenv_path=project_root / ".env")
    configure_logging(getenv("LOG_LEVEL", "INFO"))

    owner_telegram_id = require_owner_telegram_id()
    bot_token = require_env("BOT_TOKEN")
    db_url = require_env("BOT_DB_URL")
    redis_url = require_env("REDIS_URL")
    ai_db_url = require_env("AI_DB_URL")
    ai_model = require_env("AI_MODEL")
    owner_timezone = ZoneInfo(getenv("OWNER_TIMEZONE", "Asia/Almaty"))

    voice_recognition_url = getenv("VOICE_RECOGNITION_URL", "http://localhost:8000")
    voice_recognition_api_key = getenv("VOICE_RECOGNITION_API_KEY")
    voice_recognition_mode = getenv("VOICE_RECOGNITION_MODE", "http")
    whisper_model = getenv("WHISPER_MODEL", "small")

    data_dir = project_root / "data"

    app = BotApplication(
        bot_token=bot_token,
        database_url=db_url,
        redis_url=redis_url,
        phrases_json_path=data_dir / "phrases.json",
        languages_json_path=data_dir / "languages.json",
        roles_json_path=data_dir / "roles.json",
        use_class_middlewares=True,
    )
    admit_only_owner(app, owner_telegram_id)

    attachment_store = build_attachment_store()

    dropbox_root = getenv("DROPBOX_ROOT")
    work_dir = Path(getenv("PA_WORK_DIR", str(DEFAULT_WORK_DIR)))
    start_sweeper(work_dir, dropbox_root)

    text_reader = FileTextReader()
    chat_attachments = build_chat_attachments(ai_db_url, attachment_store)
    dropbox_boundary = (
        build_dropbox_boundary(Path(dropbox_root)) if dropbox_root else None
    )

    tools: list[BaseTool] = []
    if dropbox_boundary is not None:
        tools.extend(build_dropbox_tools(dropbox_boundary, text_reader))
        tools.extend(build_dropbox_move_tools(dropbox_boundary, db_url, app))
        tools.append(
            build_dropbox_save_tool(dropbox_boundary, db_url, WorkFolder(work_dir))
        )

    wiki_factory = build_wiki_factory()
    tools.extend(build_wiki_tools(wiki_factory))
    tools.extend(build_memory_tools(wiki_factory, owner_timezone))

    todoist_token = getenv("TODOIST_TOKEN")
    if todoist_token:
        tools.extend(build_todoist_tools(todoist_token))

    mail = build_configured_gmail_client()
    if mail is not None:
        tools.extend(build_gmail_tools(mail))

    tools.extend(
        build_file_tools(
            work_folder=WorkFolder(work_dir),
            text_reader=text_reader,
            chat_attachments=chat_attachments,
            dropbox_boundary=dropbox_boundary,
            mail=mail,
        )
    )

    logger.info("AI tools: %s", ", ".join(tool.name for tool in tools))

    system_prompt_builder = SystemPromptBuilder(
        template=(data_dir / "system_prompt.txt").read_text(encoding="utf-8"),
        timezone=owner_timezone,
    )
    ai = AIApplication(
        api_key=SUBSCRIPTION_HAS_NO_API_KEY,
        provider=Provider.CLAUDE_SDK,
        model=ai_model,
        system_prompt=system_prompt_builder.build(),
        database_url=ai_db_url,
        tools=tools,
        history_turns_limit=HISTORY_TURNS_LIMIT,
        attachment_store=attachment_store,
    )

    message_sender = app.message_sender
    message_replacer = app.message_replacer

    send_to_agent_action = SendToAgentAction(
        ai=ai,
        system_prompt_builder=system_prompt_builder,
        message_sender=message_sender,
        message_replacer=message_replacer,
        message_deleter=app.message_deleter,
    )

    clear_handler = ClearCommandHandler(
        conversation_clearer=ai,
        message_sender=message_sender,
        role_repo=app.role_repo,
    )

    transcribe_voice_action = TranscribeVoiceAction(
        document_downloader=app.core.document_downloader,
        transcriber=build_transcriber(
            mode=voice_recognition_mode,
            http_base_url=voice_recognition_url,
            http_api_key=voice_recognition_api_key,
            whisper_model=whisper_model,
        ),
    )

    voice_message_handler = VoiceMessageHandler(
        transcribe_voice_action=transcribe_voice_action,
        send_to_agent_action=send_to_agent_action,
        message_sender=message_sender,
        message_replacer=message_replacer,
        message_deleter=app.message_deleter,
        role_repo=app.role_repo,
    )

    text_handler = TextMessageHandler(
        send_to_agent_action=send_to_agent_action,
        message_sender=message_sender,
        message_replacer=message_replacer,
        role_repo=app.role_repo,
    )

    photo_handler = PhotoMessageHandler(
        document_downloader=app.core.document_downloader,
        send_to_agent_action=send_to_agent_action,
        message_sender=message_sender,
        message_replacer=message_replacer,
        role_repo=app.role_repo,
        max_file_bytes=MAX_ATTACHMENT_BYTES,
        max_image_bytes=MAX_IMAGE_BYTES,
    )

    document_handler = DocumentMessageHandler(
        document_downloader=app.core.document_downloader,
        send_to_agent_action=send_to_agent_action,
        message_sender=message_sender,
        message_replacer=message_replacer,
        role_repo=app.role_repo,
        max_file_bytes=MAX_ATTACHMENT_BYTES,
        max_image_bytes=MAX_IMAGE_BYTES,
    )

    app.core.message_handler_registry.register(
        handler=voice_message_handler,
        content_types=["voice", "audio"],
    )

    app.core.message_handler_registry.register(
        handler=clear_handler,
        commands=["clear"],
        content_types=["text"],
    )

    app.core.message_handler_registry.register(
        handler=photo_handler,
        content_types=["photo"],
    )

    app.core.message_handler_registry.register(
        handler=document_handler,
        content_types=["document"],
    )

    app.core.message_handler_registry.register(
        handler=text_handler,
        content_types=["text"],
    )

    with ai:
        logger.info("Starting polling...")
        app.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception:
        logger.exception("Bot crashed")
        raise
