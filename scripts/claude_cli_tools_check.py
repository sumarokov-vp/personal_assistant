# Какие инструменты видит модель: запускает CLI Claude Code так же, как ClaudeSdkProvider
# ai_framework (SDK MCP-сервер ai-framework-tools, allowed_tools, permission_mode default), и
# печатает список tools из init-сообщения CLI. Модель не зовётся: токен подставной, init
# приходит до первого запроса к API.
#
# В образе managed settings лежат в /etc/claude-code. Вне образа тот же файл из репозитория
# подключается как project settings временного рабочего каталога.
#
#     uv run python -m scripts.claude_cli_tools_check
#     docker run --rm -v "$PWD/scripts:/app/scripts:ro" --entrypoint python \
#         personal_assistant-bot:latest -m scripts.claude_cli_tools_check

import asyncio
import os
import shutil
import tempfile
from logging import INFO, basicConfig, getLogger
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKError,
    SystemMessage,
    create_sdk_mcp_server,
    query,
    tool,
)

IMAGE_MANAGED_SETTINGS = Path("/etc/claude-code/managed-settings.json")
REPO_MANAGED_SETTINGS = (
    Path(__file__).parent.parent / "deploy" / "claude-code" / "managed-settings.json"
)
logger = getLogger("claude_cli_tools_check")

MCP_SERVER_NAME = "ai-framework-tools"
PROBE_TOOL = "memory_show"


@tool(PROBE_TOOL, "Показывает память ассистента", {"page": str})
async def probe(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": "пусто"}]}


def enter_settings_sandbox() -> str:
    if IMAGE_MANAGED_SETTINGS.exists():
        return f"managed settings {IMAGE_MANAGED_SETTINGS}"
    sandbox = Path(tempfile.mkdtemp(prefix="pa-cli-tools-"))
    (sandbox / ".claude").mkdir()
    shutil.copy(REPO_MANAGED_SETTINGS, sandbox / ".claude" / "settings.json")
    os.chdir(sandbox)
    os.environ["ENABLE_CLAUDEAI_MCP_SERVERS"] = "false"
    return f"project settings {sandbox / '.claude' / 'settings.json'}"


async def init_message() -> dict[str, Any]:
    options = ClaudeAgentOptions(
        permission_mode="default",
        mcp_servers={
            MCP_SERVER_NAME: create_sdk_mcp_server(
                name=MCP_SERVER_NAME, version="1.0.0", tools=[probe]
            )
        },
        allowed_tools=[f"mcp__{MCP_SERVER_NAME}__{PROBE_TOOL}"],
        env={"CLAUDE_CODE_OAUTH_TOKEN": "cli-tools-check"},
    )
    init: dict[str, Any] = {}
    async for message in query(prompt="ok", options=options):
        if isinstance(message, SystemMessage) and message.subtype == "init":
            init = message.data
            break
    return init


def main() -> None:
    basicConfig(level=INFO, format="%(message)s")
    source = enter_settings_sandbox()
    init = asyncio.run(init_message())
    if not init:
        raise ClaudeSDKError("CLI did not send the init message")
    logger.info("settings: %s", source)
    logger.info("CLI %s", init["claude_code_version"])
    logger.info("tools: %s", init["tools"])
    logger.info("mcp servers: %s", init["mcp_servers"])


if __name__ == "__main__":
    main()
