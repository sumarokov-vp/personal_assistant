from datetime import date

import pytest

from src.ai_tools.checkup_create_task.tool import CheckupCreateTaskTool
from src.ai_tools.checkup_skip.tool import CheckupSkipTool
from src.checkup.repos.checkup_journal_repository import CheckupJournalRepository
from src.checkup.services.checkup_actions.checkup_action_service import (
    CheckupActionService,
)
from src.todoist.services.todoist_task_service.todoist_task_service import (
    TodoistTaskService,
)
from tests.checkup.fakes import FakeTodoistClient, InMemoryWiki

TODAY = date(2026, 9, 26)


@pytest.fixture
def wiki() -> InMemoryWiki:
    return InMemoryWiki()


@pytest.fixture
def todoist() -> FakeTodoistClient:
    return FakeTodoistClient()


@pytest.fixture
def service(wiki: InMemoryWiki, todoist: FakeTodoistClient) -> CheckupActionService:
    return CheckupActionService(
        journal=CheckupJournalRepository(wiki),
        task_creator=TodoistTaskService(todoist),
        today=lambda: TODAY,
    )


@pytest.fixture
def create_tool(service: CheckupActionService) -> CheckupCreateTaskTool:
    return CheckupCreateTaskTool(service)


@pytest.fixture
def skip_tool(service: CheckupActionService) -> CheckupSkipTool:
    return CheckupSkipTool(service)
