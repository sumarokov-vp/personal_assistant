import json

import httpx
from ai_framework import ToolContext

from src.ai_tools.task_link.tool import TaskLinkInput
from src.cases.repos.cases_http_client import CasesHttpClient
from src.todoist.repos import TodoistHttpClient
from tests.task_mirror.fakes import StatefulCasesService, StatefulTodoist
from workers.bot.todoist_tools_factory import build_task_link_tool

CONTEXT = ToolContext({"chat_id": 1, "user_id": 1})


def test_task_of_another_task_manager_is_refused_without_writing_event() -> None:
    cases_service = StatefulCasesService()
    todoist_service = StatefulTodoist()
    tool = build_task_link_tool(
        TodoistHttpClient(
            "token", transport=httpx.MockTransport(todoist_service.handle)
        ),
        CasesHttpClient(
            base_url="http://cases.test",
            api_key="key",
            transport=httpx.MockTransport(cases_service.handle),
        ),
    )

    output = tool.execute(TaskLinkInput(task_ref="trello:42"), CONTEXT)

    assert "trello:42" in json.loads(output)["error"]
    assert cases_service.sent("POST", "/events") == []
    assert todoist_service.requests == []
