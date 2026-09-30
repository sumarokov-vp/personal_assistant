from src.cases.repos.cases_http_client import CasesHttpClient
from src.todoist.repos import TodoistHttpClient
from workers.bot.todoist_tools_factory import build_todoist_tools


def test_task_manager_keeps_only_reading_tools_without_cases() -> None:
    names = [
        tool.name for tool in build_todoist_tools(TodoistHttpClient("token"), None)
    ]

    assert names == ["find_tasks", "read_task"]


def test_task_manager_tools_with_cases_have_no_todoist_in_names() -> None:
    cases = CasesHttpClient(base_url="http://cases.test", api_key="key")

    names = [
        tool.name for tool in build_todoist_tools(TodoistHttpClient("token"), cases)
    ]

    assert names == ["find_tasks", "read_task", "task_link"]
