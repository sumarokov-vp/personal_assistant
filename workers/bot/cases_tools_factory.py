from zoneinfo import ZoneInfo

from ai_framework import BaseTool

from src.ai_tools import (
    CaseAddEventTool,
    CaseFindTool,
    CaseOpenTool,
    CaseReadTool,
    CaseUpdateTool,
    TaskAddTool,
    TaskCloseTool,
    TaskListTool,
    TaskUpdateTool,
)
from src.ai_tools.task_add.protocols import ITaskRecordedListener
from src.ai_tools.task_close.protocols import ITaskClosedListener
from src.ai_tools.task_update.protocols import ITaskChangedListener
from src.cases.repos.cases_http_client import CasesHttpClient
from src.cases.services.untrusted_frame.untrusted_case_frame import UntrustedCaseFrame

CASES_VARIABLES = ("CASES_API_URL", "CASES_API_KEY")


def build_cases_client(api_url: str, api_key: str) -> CasesHttpClient:
    return CasesHttpClient(base_url=api_url, api_key=api_key)


def build_cases_tools(
    cases: CasesHttpClient,
    timezone: ZoneInfo,
    task_recorded: ITaskRecordedListener | None = None,
    task_changed: ITaskChangedListener | None = None,
    task_closed: ITaskClosedListener | None = None,
) -> list[BaseTool]:
    frame = UntrustedCaseFrame()
    return [
        CaseFindTool(finder=cases, frame=frame, timezone=timezone),
        CaseOpenTool(opener=cases),
        CaseReadTool(reader=cases, frame=frame, timezone=timezone),
        CaseAddEventTool(adder=cases, timezone=timezone),
        CaseUpdateTool(updater=cases),
        TaskAddTool(adder=cases, timezone=timezone, listener=task_recorded),
        TaskListTool(lister=cases, frame=frame),
        TaskUpdateTool(updater=cases, listener=task_changed),
        TaskCloseTool(closer=cases, timezone=timezone, listener=task_closed),
    ]
