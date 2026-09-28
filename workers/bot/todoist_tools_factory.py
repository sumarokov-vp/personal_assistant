from ai_framework import BaseTool

from src.ai_tools import FindTasksTool, ReadTaskTool, TaskLinkTodoistTool
from src.cases.repos.cases_http_client import CasesHttpClient
from src.task_mirror.services.inbound_sync import TodoistInboundSync
from src.task_mirror.services.mirror_pass import TodoistMirrorPass
from src.task_mirror.services.outbound_mirror import (
    TaskMirrorListener,
    TodoistOutboundMirror,
)
from src.task_mirror.services.todoist_adoption import TodoistTaskAdoption
from src.todoist.repos import TodoistHttpClient
from src.todoist.services.todoist_task_service import TodoistTaskService


def build_task_mirror(
    todoist: TodoistHttpClient, cases: CasesHttpClient
) -> tuple[TaskMirrorListener, TodoistMirrorPass]:
    outbound = TodoistOutboundMirror(todoist=todoist, cases=cases)
    mirror_pass = TodoistMirrorPass(
        outbound=outbound,
        inbound=TodoistInboundSync(todoist=todoist, cases=cases),
        tasks=cases,
    )
    return TaskMirrorListener(outbound), mirror_pass


def build_todoist_client(token: str) -> TodoistHttpClient:
    return TodoistHttpClient(token)


def build_todoist_tools(
    todoist: TodoistHttpClient, cases: CasesHttpClient | None
) -> list[BaseTool]:
    tasks = TodoistTaskService(todoist)
    tools: list[BaseTool] = [
        FindTasksTool(finder=tasks),
        ReadTaskTool(reader=tasks),
    ]
    if cases is not None:
        tools.append(
            TaskLinkTodoistTool(
                adopter=TodoistTaskAdoption(todoist=todoist, cases=cases)
            )
        )
    return tools
