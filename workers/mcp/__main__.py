from logging import WARNING, basicConfig, getLogger
from os import environ
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from src.todoist.repos import TodoistHttpClient
from workers.mcp.auth.core_auth_factory import build_core_auth
from workers.mcp.core_server_factory import (
    build_core_app,
    build_core_middleware,
    build_core_server,
)
from workers.mcp.core_settings import CoreSettings
from workers.mcp.core_tools_factory import build_core_tools
from workers.mcp.journal.denial_journal import DenialJournal
from workers.mcp.journal.json_lines_file import JsonLinesFile

TOKEN_LEAKING_LOGGERS = ("httpx", "httpcore", "urllib3", "requests")

logger = getLogger(__name__)


def configure_logging(level: str) -> None:
    basicConfig(level=level.upper())
    for name in TOKEN_LEAKING_LOGGERS:
        getLogger(name).setLevel(WARNING)


def main(settings: CoreSettings) -> None:
    tools = build_core_tools(
        todoist=TodoistHttpClient(settings.todoist_token),
        dropbox_root=settings.dropbox_root,
    )
    logger.info("MCP tools: %s", ", ".join(tool.name for tool in tools))
    settings.journal_file.parent.mkdir(parents=True, exist_ok=True)
    logger.info("MCP journal: %s", settings.journal_file)
    journal = JsonLinesFile(settings.journal_file)
    auth = build_core_auth(settings.auth, DenialJournal(journal))
    logger.info(
        "MCP auth: OIDC %s, public %s, allowed %d",
        settings.auth.oidc_config_url,
        settings.auth.public_url,
        len(settings.auth.allowed_emails),
    )
    server = build_core_server(
        tools,
        auth=auth,
        middleware=build_core_middleware(journal, settings.allowed_projects),
    )
    uvicorn.run(
        build_core_app(server),
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")
    core_settings = CoreSettings.from_env(environ)
    configure_logging(core_settings.log_level)
    try:
        main(core_settings)
    except Exception:
        logger.exception("MCP core failed")
        raise
