from zoneinfo import ZoneInfo

from src.cases.repos.cases_http_client import CasesHttpClient
from workers.bot.cases_tools_factory import build_cases_tools


def test_cases_tools_include_task_tools(client: CasesHttpClient) -> None:
    names = [tool.name for tool in build_cases_tools(client, ZoneInfo("UTC"))]

    assert {"task_add", "task_list", "task_update", "task_close"} <= set(names)
