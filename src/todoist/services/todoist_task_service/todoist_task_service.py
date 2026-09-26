from src.todoist.models.todoist_task import TodoistTask
from src.todoist.services.todoist_task_service.protocols.i_todoist_client import (
    ITodoistClient,
)
from src.todoist.services.todoist_task_service.task_card import TaskCard

ASSISTANT_LABEL = "pa"
DUE_LANG = "ru"
TASK_URL_TEMPLATE = "https://app.todoist.com/app/task/{task_id}"


class TodoistTaskService:
    def __init__(self, client: ITodoistClient) -> None:
        self._client = client

    def find(self, query: str, limit: int) -> list[TaskCard]:
        tasks = self._client.filter_tasks(query=query, limit=limit)
        if not tasks:
            return []
        project_names = self._project_names()
        return [self._card(task, project_names) for task in tasks]

    def create_assistant_task(
        self, content: str, due: str, description: str | None = None
    ) -> TaskCard:
        task = self._client.add_task(
            content=content,
            due_string=due,
            due_lang=DUE_LANG,
            labels=[ASSISTANT_LABEL],
            description=description,
        )
        return self._card(task, self._project_names())

    def _project_names(self) -> dict[str, str]:
        return {project.id: project.name for project in self._client.list_projects()}

    @staticmethod
    def _card(task: TodoistTask, project_names: dict[str, str]) -> TaskCard:
        return TaskCard(
            id=task.id,
            content=task.content,
            description=task.description,
            due=task.due,
            labels=task.labels,
            project=project_names.get(task.project_id, task.project_id),
            url=TASK_URL_TEMPLATE.format(task_id=task.id),
        )
