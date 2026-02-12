from logging import basicConfig, getLogger
from os import getenv
from pathlib import Path

from dotenv import load_dotenv

from bot_framework.app import BotApplication
from claude_agent_sdk import create_sdk_mcp_server
from src.agent.client import AgentClient
from src.agent.tools.registry import SessionRegistry
from src.agent.tools.send_file import init_send_file, send_file
from src.chat.actions.send_to_agent_action import SendToAgentAction
from src.chat.handlers.clear_command_handler import ClearCommandHandler
from src.chat.handlers.context_command_handler import ContextCommandHandler
from src.chat.handlers.text_message_handler import TextMessageHandler

logger = getLogger(__name__)


def main() -> None:
    basicConfig(level="DEBUG")

    project_root = Path(__file__).parent.parent.parent
    load_dotenv(dotenv_path=project_root / ".env")

    bot_token = getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN environment variable is required")

    db_url = getenv("BOT_DB_URL")
    if not db_url:
        raise ValueError("BOT_DB_URL environment variable is required")

    redis_url = getenv("REDIS_URL")
    if not redis_url:
        raise ValueError("REDIS_URL environment variable is required")

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

    session_registry = SessionRegistry()
    init_send_file(session_registry)
    mcp_server = create_sdk_mcp_server(
        name="bot-tools", version="1.0.0", tools=[send_file]
    )
    agent_client = AgentClient(
        session_registry=session_registry,
        bot=app.core.bot,
        mcp_server=mcp_server,
    )
    message_service = app.message_service

    send_to_agent_action = SendToAgentAction(
        agent_client=agent_client,
        message_service=message_service,
    )

    clear_handler = ClearCommandHandler(
        agent_client=agent_client,
        message_service=message_service,
        role_repo=app.role_repo,
    )

    context_handler = ContextCommandHandler(
        agent_client=agent_client,
        message_service=message_service,
        role_repo=app.role_repo,
    )

    text_handler = TextMessageHandler(
        send_to_agent_action=send_to_agent_action,
        message_service=message_service,
        role_repo=app.role_repo,
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
