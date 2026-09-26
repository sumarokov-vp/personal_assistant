from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ai_framework import AIApplication, BaseTool, Provider

from src.ai_tools import MemoryShowTool
from src.ai_tools.checkup_create_task import CheckupCreateTaskTool
from src.ai_tools.checkup_skip import CheckupSkipTool
from src.ai_tools.find_tasks import FindTasksTool
from src.chat.actions.system_prompt_builder import SystemPromptBuilder
from src.checkup.repos import CheckupJournalRepository
from src.checkup.services.checkup_actions import CheckupActionService
from src.memory.repos import (
    CommitmentRepository,
    DeadlineRepository,
    IWikiStorage,
    WhereaboutsRepository,
)
from src.todoist.repos import TodoistHttpClient
from src.todoist.services.todoist_task_service import TodoistTaskService
from workers.checkup.checkup_env import CheckupEnv
from workers.checkup.checkup_pass import CheckupPass
from workers.checkup.checkup_report import CheckupReport
from workers.checkup.memory_fill_step import MemoryFillStep
from workers.memory_fill.composition import (
    SUBSCRIPTION_HAS_NO_API_KEY,
    build_wiki_storage,
)

CHECKUP_PROMPT_PATH = (
    Path(__file__).parent.parent.parent / "data" / "checkup_prompt.txt"
)


def build_checkup_actions(
    storage: IWikiStorage, tasks: TodoistTaskService, today: Callable[[], date]
) -> CheckupActionService:
    return CheckupActionService(
        journal=CheckupJournalRepository(storage), task_creator=tasks, today=today
    )


def build_checkup_tools(
    storage: IWikiStorage, tasks: TodoistTaskService, actions: CheckupActionService
) -> list[BaseTool]:
    return [
        MemoryShowTool(
            deadlines=DeadlineRepository(storage),
            whereabouts=WhereaboutsRepository(storage),
            commitments=CommitmentRepository(storage),
        ),
        FindTasksTool(finder=tasks),
        CheckupCreateTaskTool(actions),
        CheckupSkipTool(actions),
    ]


def build_checkup_system_prompt(template: str, timezone: ZoneInfo) -> str:
    return SystemPromptBuilder(template=template, timezone=timezone).build()


def owner_today(timezone: ZoneInfo) -> Callable[[], date]:
    return lambda: datetime.now(tz=timezone).date()


def new_thread_id() -> str:
    return f"checkup:{datetime.now(tz=UTC):%Y%m%dT%H%M%S}"


def run_checkup(
    env: CheckupEnv, fill_prompt_template: str, checkup_prompt_template: str
) -> CheckupReport:
    fill_env = env.memory_fill
    storage = build_wiki_storage(fill_env.wiki)
    tasks = TodoistTaskService(TodoistHttpClient(env.todoist_token))
    actions = build_checkup_actions(
        storage, tasks, owner_today(fill_env.owner_timezone)
    )
    ai = AIApplication(
        api_key=SUBSCRIPTION_HAS_NO_API_KEY,
        provider=Provider.CLAUDE_SDK,
        model=fill_env.ai_model,
        system_prompt=build_checkup_system_prompt(
            checkup_prompt_template, fill_env.owner_timezone
        ),
        database_url=fill_env.ai_db_url,
        tools=build_checkup_tools(storage, tasks, actions),
        max_tool_rounds=env.max_tool_rounds,
    )
    checkup = CheckupPass(
        memory_fill=MemoryFillStep(fill_env, fill_prompt_template),
        conversation=ai,
        thread_id=new_thread_id(),
    )
    with ai:
        return checkup.execute()
