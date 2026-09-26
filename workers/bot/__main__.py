import tempfile
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
from src.chat.actions.send_to_agent_action import SendToAgentAction
from src.chat.actions.system_prompt_builder import SystemPromptBuilder
from src.chat.actions.transcribe_voice_action import TranscribeVoiceAction
from src.chat.handlers.clear_command_handler import ClearCommandHandler
from src.chat.handlers.document_message_handler import DocumentMessageHandler
from src.chat.handlers.photo_message_handler import PhotoMessageHandler
from src.chat.handlers.text_message_handler import TextMessageHandler
from src.chat.handlers.voice_message_handler import VoiceMessageHandler
from workers.bot.transcriber_factory import build_transcriber

logger = getLogger(__name__)

TOKEN_LEAKING_LOGGERS = ["TeleBot", "urllib3", "requests", "httpx", "anthropic"]

HISTORY_TURNS_LIMIT = 10


def configure_logging(level: str) -> None:
    basicConfig(level=level.upper())
    for name in TOKEN_LEAKING_LOGGERS:
        getLogger(name).setLevel(WARNING)


def require_env(name: str) -> str:
    value = getenv(name)
    if not value:
        raise ValueError(f"{name} environment variable is required")
    return value


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
    inbox_dir = Path(tempfile.gettempdir()) / "personal_assistant_inbox"
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

    tools: list[BaseTool] = []

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
