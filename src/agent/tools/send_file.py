from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from src.agent.tools.registry import SessionRegistry
from src.agent.tools.workspace_file_reader import WorkspaceFileReader

_registry: SessionRegistry | None = None
_file_reader: WorkspaceFileReader | None = None


def init_send_file(registry: SessionRegistry, file_reader: WorkspaceFileReader) -> None:
    global _registry, _file_reader  # noqa: PLW0603
    _registry = registry
    _file_reader = file_reader


@tool(
    "send_file",
    "Send a file from the workspace directory to the user in Telegram. "
    "Only files inside the workspace can be sent; the path may be absolute or relative to the workspace.",
    {"file_path": str},
)
async def send_file(args: dict[str, Any]) -> dict[str, Any]:
    if _registry is None or _file_reader is None:
        raise ValueError("send_file tool is not initialized, call init_send_file first")

    file_bytes = _file_reader.read(args["file_path"])
    file_name = Path(args["file_path"]).name

    context = _registry.get_current_context()
    context.document_sender.send_document(
        chat_id=context.chat_id,
        document=file_bytes,
        filename=file_name,
    )

    return {"content": [{"type": "text", "text": f"File sent successfully: {file_name}"}]}
