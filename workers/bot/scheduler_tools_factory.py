from zoneinfo import ZoneInfo

from ai_framework import BaseTool

from src.ai_tools import ScheduleAddTool, ScheduleCancelTool, ScheduleListTool
from src.ai_tools.schedule_list.protocols import ICaseFinder
from src.scheduler.repos.scheduler_http_client import SchedulerHttpClient

SCHEDULER_API_VARIABLES = ("SCHEDULER_API_URL", "SCHEDULER_API_KEY")


def build_scheduler_client(api_url: str, api_key: str) -> SchedulerHttpClient:
    return SchedulerHttpClient(base_url=api_url, api_key=api_key)


def build_scheduler_tools(
    scheduler: SchedulerHttpClient,
    timezone: ZoneInfo,
    cases: ICaseFinder | None = None,
) -> list[BaseTool]:
    return [
        ScheduleAddTool(creator=scheduler, timezone=timezone),
        ScheduleListTool(lister=scheduler, timezone=timezone, cases=cases),
        ScheduleCancelTool(canceller=scheduler),
    ]
