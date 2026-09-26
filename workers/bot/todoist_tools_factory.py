from ai_framework import BaseTool

from src.ai_tools import (
    AddTaskLinkTool,
    CreateTaskTool,
    FindTasksTool,
    ReadTaskTool,
    UpdateTaskTool,
)
from src.todoist.repos import TodoistHttpClient
from src.todoist.services.todoist_task_service import TodoistTaskService


def build_todoist_tools(token: str) -> list[BaseTool]:
    tasks = TodoistTaskService(TodoistHttpClient(token))
    return [
        FindTasksTool(finder=tasks),
        CreateTaskTool(creator=tasks),
        ReadTaskTool(reader=tasks),
        AddTaskLinkTool(adder=tasks),
        UpdateTaskTool(updater=tasks),
    ]
