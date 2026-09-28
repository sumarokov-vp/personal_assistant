from src.todoist.repos import TodoistHttpClient
from workers.bot.todoist_tools_factory import build_todoist_tools


def test_todoist_keeps_only_reading_tools_without_cases() -> None:
    names = [
        tool.name for tool in build_todoist_tools(TodoistHttpClient("token"), None)
    ]

    assert names == ["find_tasks", "read_task"]
