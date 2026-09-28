from zoneinfo import ZoneInfo

from ai_framework import BaseTool

from src.ai_tools import (
    CaseAddEventTool,
    CaseFindTool,
    CaseOpenTool,
    CaseReadTool,
    CaseUpdateTool,
)
from src.cases.repos.cases_http_client import CasesHttpClient
from src.cases.services.untrusted_frame.untrusted_case_frame import UntrustedCaseFrame

CASES_VARIABLES = ("CASES_API_URL", "CASES_API_KEY")


def build_cases_client(api_url: str, api_key: str) -> CasesHttpClient:
    return CasesHttpClient(base_url=api_url, api_key=api_key)


def build_cases_tools(cases: CasesHttpClient, timezone: ZoneInfo) -> list[BaseTool]:
    frame = UntrustedCaseFrame()
    return [
        CaseFindTool(finder=cases, frame=frame, timezone=timezone),
        CaseOpenTool(opener=cases),
        CaseReadTool(reader=cases, frame=frame, timezone=timezone),
        CaseAddEventTool(adder=cases, timezone=timezone),
        CaseUpdateTool(updater=cases),
    ]
