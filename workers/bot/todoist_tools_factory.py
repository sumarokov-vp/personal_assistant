from ai_framework import BaseTool

from src.ai_tools.create_task import CreateTaskTool
from src.ai_tools.find_tasks import FindTasksTool
from src.todoist.repos import TodoistHttpClient
from src.todoist.services.todoist_task_service import TodoistTaskService


def build_todoist_tools(token: str) -> list[BaseTool]:
    tasks = TodoistTaskService(TodoistHttpClient(token))
    return [
        FindTasksTool(finder=tasks),
        CreateTaskTool(creator=tasks),
    ]
