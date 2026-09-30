from zoneinfo import ZoneInfo

import httpx
import pytest
from ai_framework import BaseTool

from src.cases.repos.cases_http_client import CasesHttpClient
from src.task_mirror.services.mirror_pass import MirrorPass
from src.todoist.repos import TodoistHttpClient
from tests.task_mirror.fakes import StatefulCasesService, StatefulTodoist
from workers.bot.__main__ import build_task_rescheduler
from workers.bot.cases_tools_factory import build_cases_tools
from workers.bot.todoist_tools_factory import build_task_mirror, build_todoist_tools


@pytest.fixture
def cases_service() -> StatefulCasesService:
    return StatefulCasesService()


@pytest.fixture
def todoist_service() -> StatefulTodoist:
    return StatefulTodoist()


@pytest.fixture
def cases(cases_service: StatefulCasesService) -> CasesHttpClient:
    return CasesHttpClient(
        base_url="http://cases.test",
        api_key="key",
        transport=httpx.MockTransport(cases_service.handle),
    )


@pytest.fixture
def todoist(todoist_service: StatefulTodoist) -> TodoistHttpClient:
    return TodoistHttpClient(
        "secret-token", transport=httpx.MockTransport(todoist_service.handle)
    )


@pytest.fixture
def mirrored_tools(
    cases: CasesHttpClient, todoist: TodoistHttpClient
) -> dict[str, BaseTool]:
    listener, _ = build_task_mirror(todoist, cases)
    tools = build_cases_tools(
        cases,
        ZoneInfo("UTC"),
        task_recorded=listener,
        task_changed=listener,
        task_closed=listener,
        task_planner=build_task_rescheduler(todoist, cases),
    )
    tools.extend(build_todoist_tools(todoist, cases))
    return {tool.name: tool for tool in tools}


@pytest.fixture
def mirror_pass(cases: CasesHttpClient, todoist: TodoistHttpClient) -> MirrorPass:
    _, mirror_pass = build_task_mirror(todoist, cases)
    return mirror_pass


@pytest.fixture
def standalone_tools(cases: CasesHttpClient) -> dict[str, BaseTool]:
    return {tool.name: tool for tool in build_cases_tools(cases, ZoneInfo("UTC"))}
