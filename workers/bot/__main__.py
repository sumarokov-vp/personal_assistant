from logging import WARNING, basicConfig, getLogger
from os import getenv
from pathlib import Path
from zoneinfo import ZoneInfo

from ai_framework import AIApplication, BaseTool, Provider
from dotenv import load_dotenv

from bot_framework.app import BotApplication
from bot_framework.features.flows.request_role_flow.handlers import (
    RequestRoleCommandHandler,
)
from src.ai_tools.dropbox_propose_moves import DropboxProposeMovesTool
from src.ai_tools.dropbox_read import DropboxReadTool
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
from src.dropbox.services.search.dropbox_search import DropboxSearch
from src.dropbox.services.tree.dropbox_tree import DropboxTree
from src.flows.dropbox_moves import (
    CancelMovePlanHandler,
    ExecuteMovePlanHandler,
    MovePlanCallbackGuard,
    MovePlanCardPresenter,
    MovePlanCardText,
    RollbackMovePlanHandler,
)
from workers.bot.transcriber_factory import build_transcriber

logger = getLogger(__name__)

TOKEN_LEAKING_LOGGERS = ["TeleBot", "urllib3", "requests", "httpx", "anthropic"]

HISTORY_TURNS_LIMIT = 10
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
CARD_LANGUAGE = "ru"


def configure_logging(level: str) -> None:
    basicConfig(level=level.upper())
    for name in TOKEN_LEAKING_LOGGERS:
        getLogger(name).setLevel(WARNING)


def require_env(name: str) -> str:
    value = getenv(name)
    if not value:
        raise ValueError(f"{name} environment variable is required")
    return value


def build_dropbox_tools(root: Path) -> list[BaseTool]:
    if not root.is_dir():
        raise ValueError(f"DROPBOX_ROOT={root} is not a directory")
    boundary = DropboxBoundary(root=root, policy=DropboxAccessPolicy())
    return [
        DropboxTreeTool(tree_builder=DropboxTree(boundary=boundary)),
        DropboxSearchTool(finder=DropboxSearch(boundary=boundary)),
        DropboxReadTool(reader=DropboxReader(boundary=boundary)),
    ]


def build_dropbox_move_tools(
    root: Path, database_url: str, app: BotApplication
) -> list[BaseTool]:
    apply_migrations(database_url)
    boundary = DropboxBoundary(root=root, policy=DropboxAccessPolicy())
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


def main() -> None:
    project_root = Path(__file__).parent.parent.parent
    load_dotenv(dotenv_path=project_root / ".env")
    configure_logging(getenv("LOG_LEVEL", "INFO"))

    bot_token = require_env("BOT_TOKEN")
    db_url = require_env("BOT_DB_URL")
    redis_url = require_env("REDIS_URL")
    ai_db_url = require_env("AI_DB_URL")
    anthropic_api_key = require_env("ANTHROPIC_API_KEY")
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

    tools: list[BaseTool] = []
    dropbox_root = getenv("DROPBOX_ROOT")
    if dropbox_root:
        tools.extend(build_dropbox_tools(Path(dropbox_root)))
        tools.extend(build_dropbox_move_tools(Path(dropbox_root), db_url, app))

    system_prompt_builder = SystemPromptBuilder(
        template=(data_dir / "system_prompt.txt").read_text(encoding="utf-8"),
        timezone=owner_timezone,
    )
    ai = AIApplication(
        api_key=anthropic_api_key,
        provider=Provider.ANTHROPIC,
        model=ai_model,
        system_prompt=system_prompt_builder.build(),
        database_url=ai_db_url,
        tools=tools,
        history_turns_limit=HISTORY_TURNS_LIMIT,
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

    request_role_handler = RequestRoleCommandHandler(
        request_role_flow_router=app.request_role_flow_router,
        user_repo=app.user_repo,
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
        message_sender=message_sender,
        role_repo=app.role_repo,
        max_file_bytes=MAX_ATTACHMENT_BYTES,
    )

    document_handler = DocumentMessageHandler(
        document_downloader=app.core.document_downloader,
        send_to_agent_action=send_to_agent_action,
        message_sender=message_sender,
        message_replacer=message_replacer,
        role_repo=app.role_repo,
        max_file_bytes=MAX_ATTACHMENT_BYTES,
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
        handler=request_role_handler,
        commands=["request_role"],
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
