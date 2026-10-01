from collections.abc import Iterable

from ai_framework import BaseTool

OUTBOUND_TOOLS = frozenset({"colleague_send"})
SCHEDULE_TOOL_PREFIX = "schedule_"


def scheduled_run_tools(bot_tools: Iterable[BaseTool]) -> list[BaseTool]:
    return [tool for tool in bot_tools if _allowed_without_owner(tool.name)]


def _allowed_without_owner(name: str) -> bool:
    return name not in OUTBOUND_TOOLS and not name.startswith(SCHEDULE_TOOL_PREFIX)
