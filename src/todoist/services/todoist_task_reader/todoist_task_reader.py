from datetime import datetime

from src.task_manager.models.managed_task import ManagedTask
from src.task_manager.models.managed_task_details import ManagedTaskDetails
from src.task_manager.models.task_comment import TaskComment
from src.task_manager.models.task_manager_identity import TaskManagerIdentity
from src.task_manager.models.task_search import TaskSearch
from src.todoist.models.todoist_task import TodoistTask
from src.todoist.services.entities.todoist_identity import TODOIST_IDENTITY
from src.todoist.services.entities.todoist_ref import TodoistRef
from src.todoist.services.entities.todoist_task_converter import TodoistTaskConverter
from src.todoist.services.todoist_task_reader.protocols.i_todoist_read_client import (
    ITodoistReadClient,
)
from src.todoist.services.todoist_task_reader.todoist_filter_query import (
    TodoistFilterQuery,
)


class TodoistTaskReader:
    def __init__(self, client: ITodoistReadClient) -> None:
        self._client = client

    @property
    def identity(self) -> TaskManagerIdentity:
        return TODOIST_IDENTITY

    def find_tasks(self, search: TaskSearch) -> list[ManagedTask]:
        tasks = self._client.filter_tasks(
            query=TodoistFilterQuery.of(search), limit=search.limit
        )
        if not tasks:
            return []
        return self._managed(tasks, self._project_names())

    def get_task(self, ref: str) -> ManagedTask:
        task = self._client.get_task(TodoistRef.task_id(ref))
        [managed] = self._managed([task], self._project_names())
        return managed

    def read_task(self, ref: str) -> ManagedTaskDetails:
        task_id = TodoistRef.task_id(ref)
        task = self._client.get_task(task_id)
        subtasks = self._client.list_subtasks(task_id)
        project_names = self._project_names()
        [managed] = self._managed([task], project_names)
        return ManagedTaskDetails(
            task=managed,
            subtasks=self._managed(subtasks, project_names),
            comments=[
                TaskComment(
                    text=comment.content,
                    posted_at=datetime.fromisoformat(comment.posted_at),
                )
                for comment in self._client.list_comments(task_id)
            ],
        )

    def _project_names(self) -> dict[str, str]:
        return {project.id: project.name for project in self._client.list_projects()}

    @staticmethod
    def _managed(
        tasks: list[TodoistTask], project_names: dict[str, str]
    ) -> list[ManagedTask]:
        return [
            TodoistTaskConverter.managed(
                task, project_names.get(task.project_id, task.project_id)
            )
            for task in tasks
        ]
