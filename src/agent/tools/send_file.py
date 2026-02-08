from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from src.agent.tools.registry import SessionRegistry

_registry: SessionRegistry | None = None


def init_send_file(registry: SessionRegistry) -> None:
    global _registry  # noqa: PLW0603
    _registry = registry


@tool("send_file", "Send a file to the user in Telegram", {"file_path": str})
async def send_file(args: dict[str, Any]) -> dict[str, Any]:
    if _registry is None:
        raise ValueError("send_file tool is not initialized, call init_send_file first")

    file_path = Path(args["file_path"])
    if not file_path.exists():
        return {
            "content": [{"type": "text", "text": f"File not found: {file_path}"}],
            "isError": True,
        }

    context = _registry.get_current_context()
    with open(file_path, "rb") as f:
        context.bot.send_document(context.chat_id, f)

    return {
        "content": [
            {"type": "text", "text": f"File sent successfully: {file_path.name}"}
        ]
    }
