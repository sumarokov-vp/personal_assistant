import ctypes
import sys
from logging import WARNING, basicConfig, getLogger
from os import getenv
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

from bot_framework.app import BotApplication
from bot_framework.features.flows.request_role_flow.handlers import RequestRoleCommandHandler
from claude_agent_sdk import create_sdk_mcp_server
from src.agent.agent_options_factory import AgentOptionsFactory
from src.agent.client import AgentClient
from src.agent.sdk_client_pool import SDKClientPool
from src.agent.tools.registry import SessionRegistry
from src.agent.tools.send_file import init_send_file, send_file
from src.agent.tools.workspace_file_reader import WorkspaceFileReader
from src.chat.actions.send_to_agent_action import SendToAgentAction
from src.chat.actions.transcribe_voice_action import TranscribeVoiceAction
from src.chat.handlers.clear_command_handler import ClearCommandHandler
from src.chat.handlers.context_command_handler import ContextCommandHandler
from src.chat.handlers.document_message_handler import DocumentMessageHandler
from src.chat.handlers.photo_message_handler import PhotoMessageHandler
from src.chat.handlers.text_message_handler import TextMessageHandler
from src.chat.handlers.voice_message_handler import VoiceMessageHandler
from src.voice_recognition.transcript_cleaner import TranscriptCleaner
from workers.bot.transcriber_factory import build_transcriber

logger = getLogger(__name__)

TOKEN_LEAKING_LOGGERS = ["TeleBot", "urllib3", "requests"]

# Временно: коннекторы claude.ai, открытые агенту бота. Остальные (Drive, Slack, Docs и пр.) закрыты
AGENT_ALLOWED_MCP_SERVERS = ["claude_ai_Gmail", "claude_ai_Google_Calendar"]

BOT_SECRET_ENV_VARS = ["BOT_TOKEN", "BOT_DB_URL", "REDIS_URL", "VOICE_RECOGNITION_API_KEY"]

# CLAUDE_CODE_OAUTH_TOKEN сюда не входит: пустое значение затёрло бы авторизацию CLI.
# Из окружения Bash его вычищает сам CLI (CLAUDE_CODE_SUBPROCESS_ENV_SCRUB в AgentOptionsFactory)


def agent_protected_paths(project_root: Path) -> list[Path]:
    home = Path.home()
    return [
        home / ".password-store",
        home / ".local" / "share" / "password-store",
        home / ".gnupg",
        home / ".ssh",
        home / "Vault",
        Path("/Volumes/Vault"),
        home / ".claude" / ".credentials.json",
        home / ".claude" / "projects",
        home / ".claude" / "history.jsonl",
        home / ".config",
        home / ".aws",
        home / ".docker",
        home / ".netrc",
        home / ".kube",
        home / ".colima",
        home / ".lima",
        home / "Library" / "Keychains",
        project_root / ".env",
    ]


PR_SET_DUMPABLE = 4


def hide_process_environment() -> None:
    # Без песочницы (контейнер) Bash агента работает под тем же uid, что и бот, и мог бы прочитать
    # секреты из /proc/<pid бота>/environ. Недампабельный процесс закрывает свой /proc от того же uid.
    if sys.platform == "linux":
        ctypes.CDLL(None).prctl(PR_SET_DUMPABLE, 0, 0, 0, 0)


def configure_logging(level: str) -> None:
    basicConfig(level=level.upper())
    for name in TOKEN_LEAKING_LOGGERS:
        getLogger(name).setLevel(WARNING)


def main() -> None:
    hide_process_environment()
    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / ".env"
    load_dotenv(dotenv_path=env_path)
    configure_logging(getenv("LOG_LEVEL", "INFO"))

    bot_token = getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN environment variable is required")

    db_url = getenv("BOT_DB_URL")
    if not db_url:
        raise ValueError("BOT_DB_URL environment variable is required")

    redis_url = getenv("REDIS_URL")
    if not redis_url:
        raise ValueError("REDIS_URL environment variable is required")

    voice_recognition_url = getenv("VOICE_RECOGNITION_URL", "http://localhost:8000")
    voice_recognition_api_key = getenv("VOICE_RECOGNITION_API_KEY")
    voice_recognition_mode = getenv("VOICE_RECOGNITION_MODE", "http")
    whisper_model = getenv("WHISPER_MODEL", "small")

    data_dir = project_root / "data"
    workspace_dir = project_root / "workspace"
    inbox_dir = workspace_dir / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    app = BotApplication(
        bot_token=bot_token,
        database_url=db_url,
        redis_url=redis_url,
        phrases_json_path=data_dir / "phrases.json",
        languages_json_path=data_dir / "languages.json",
        roles_json_path=data_dir / "roles.json",
        use_class_middlewares=True,
    )

    session_registry = SessionRegistry()
    init_send_file(session_registry, WorkspaceFileReader(workspace_dir))
    mcp_server = create_sdk_mcp_server(
        name="bot-tools", version="1.0.0", tools=[send_file]
    )
    agent_options_factory = AgentOptionsFactory(
        workspace_dir=workspace_dir,
        protected_paths=agent_protected_paths(project_root),
        hidden_env_vars=sorted({*BOT_SECRET_ENV_VARS, *dotenv_values(env_path)}),
        allowed_mcp_servers=AGENT_ALLOWED_MCP_SERVERS,
        sandbox_enabled=getenv("AGENT_SANDBOX", "true").lower() != "false",
        mcp_server=mcp_server,
    )
    pool = SDKClientPool(options_factory=agent_options_factory)
    agent_client = AgentClient(
        pool=pool,
        session_registry=session_registry,
        document_sender=app.document_sender,
    )
    message_sender = app.message_sender
    message_replacer = app.message_replacer

    send_to_agent_action = SendToAgentAction(
        agent_client=agent_client,
        message_sender=message_sender,
        message_replacer=message_replacer,
    )

    clear_handler = ClearCommandHandler(
        agent_client=agent_client,
        message_sender=message_sender,
        role_repo=app.role_repo,
    )

    context_handler = ContextCommandHandler(
        agent_client=agent_client,
        message_sender=message_sender,
        role_repo=app.role_repo,
    )

    request_role_handler = RequestRoleCommandHandler(
        request_role_flow_router=app.request_role_flow_router,
        user_repo=app.user_repo,
    )

    transcribe_voice_action = TranscribeVoiceAction(
        transcriber=build_transcriber(
            mode=voice_recognition_mode,
            http_base_url=voice_recognition_url,
            http_api_key=voice_recognition_api_key,
            whisper_model=whisper_model,
        ),
        transcript_cleaner=TranscriptCleaner(workspace_dir=workspace_dir),
        document_sender=app.document_sender,
        message_replacer=app.message_replacer,
    )

    voice_message_handler = VoiceMessageHandler(
        document_downloader=app.core.document_downloader,
        transcribe_voice_action=transcribe_voice_action,
        message_sender=app.message_sender,
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
        inbox_dir=inbox_dir,
    )

    document_handler = DocumentMessageHandler(
        document_downloader=app.core.document_downloader,
        send_to_agent_action=send_to_agent_action,
        message_sender=message_sender,
        message_replacer=message_replacer,
        role_repo=app.role_repo,
        inbox_dir=inbox_dir,
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
        handler=context_handler,
        commands=["context"],
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
