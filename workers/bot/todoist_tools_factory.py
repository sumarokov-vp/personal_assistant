from ai_framework import BaseTool

from src.ai_tools import FindTasksTool, ReadTaskTool, TaskLinkTool
from src.cases.repos.cases_http_client import CasesHttpClient
from src.task_mirror.services.inbound_sync import InboundSync
from src.task_mirror.services.mirror_pass import MirrorPass
from src.task_mirror.services.outbound_mirror import OutboundMirror, TaskMirrorListener
from src.task_mirror.services.task_adoption import TaskAdoption
from src.todoist.repos import TodoistHttpClient
from src.todoist.services.todoist_change_feed import TodoistChangeFeed
from src.todoist.services.todoist_task_reader import TodoistTaskReader
from src.todoist.services.todoist_task_reader.protocols import ITodoistReadClient
from src.todoist.services.todoist_task_writer import TodoistTaskWriter


def build_task_mirror(
    todoist: TodoistHttpClient, cases: CasesHttpClient
) -> tuple[TaskMirrorListener, MirrorPass]:
    outbound = OutboundMirror(tasks=TodoistTaskWriter(todoist), cases=cases)
    mirror_pass = MirrorPass(
        outbound=outbound,
        inbound=InboundSync(tasks=TodoistChangeFeed(todoist), cases=cases),
        tasks=cases,
    )
    return TaskMirrorListener(outbound), mirror_pass


def build_todoist_client(token: str) -> TodoistHttpClient:
    return TodoistHttpClient(token)


def build_todoist_tools(
    todoist: TodoistHttpClient, cases: CasesHttpClient | None
) -> list[BaseTool]:
    tasks = TodoistTaskReader(todoist)
    tools: list[BaseTool] = [
        FindTasksTool(finder=tasks),
        ReadTaskTool(reader=tasks),
    ]
    if cases is not None:
        tools.append(build_task_link_tool(todoist, cases))
    return tools


def build_task_link_tool(
    todoist: ITodoistReadClient, cases: CasesHttpClient
) -> TaskLinkTool:
    return TaskLinkTool(
        adopter=TaskAdoption(tasks=TodoistTaskReader(todoist), cases=cases)
    )
