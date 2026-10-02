import re
from pathlib import Path

import pytest
from ai_framework.protocols.base_tool import BaseTool

from src.ai_tools.dropbox_read import DropboxReadTool
from src.ai_tools.dropbox_search import DropboxSearchTool
from src.ai_tools.dropbox_tree import DropboxTreeTool
from src.ai_tools.find_tasks import FindTasksTool
from src.ai_tools.read_task import ReadTaskTool

CORE_TOOLS: list[type[BaseTool]] = [
    FindTasksTool,
    ReadTaskTool,
    DropboxTreeTool,
    DropboxSearchTool,
    DropboxReadTool,
]
CORE_TOOL_NAMES = {tool.name for tool in CORE_TOOLS}
SOURCE_ROOT = Path(__file__).parents[2] / "src"
TOOL_NAME_DECLARATION = re.compile(r'name: ClassVar\[str\] = "([a-z0-9_]+)"')
FORBIDDEN_WORDS = ("Todoist", "владел")


def _declared_tool_names() -> set[str]:
    return {
        match
        for source in SOURCE_ROOT.rglob("*.py")
        for match in TOOL_NAME_DECLARATION.findall(source.read_text())
    }


def test_declared_tool_names_are_found() -> None:
    assert CORE_TOOL_NAMES < _declared_tool_names()


@pytest.mark.parametrize("tool", CORE_TOOLS, ids=lambda tool: tool.name)
def test_description_names_only_core_tools(tool: type[BaseTool]) -> None:
    foreign_names = _declared_tool_names() - CORE_TOOL_NAMES
    mentioned = {
        name
        for name in foreign_names
        if re.search(rf"(?<![a-z0-9_]){name}(?![a-z0-9_])", tool.description)
    }
    assert mentioned == set()


@pytest.mark.parametrize("tool", CORE_TOOLS, ids=lambda tool: tool.name)
def test_description_has_no_vendor_or_owner(tool: type[BaseTool]) -> None:
    lowered = tool.description.lower()
    assert [word for word in FORBIDDEN_WORDS if word.lower() in lowered] == []
