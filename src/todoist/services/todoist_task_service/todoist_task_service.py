from typing import Any

from src.todoist.models.todoist_comment import TodoistComment
from src.todoist.models.todoist_task import TodoistTask
from src.todoist.models.todoist_task_update import TodoistTaskUpdate
from src.todoist.services.entities.todoist_identity import (
    ASSISTANT_LABEL,
    TASK_URL_TEMPLATE,
)
from src.todoist.services.todoist_task_service.protocols.i_todoist_client import (
    ITodoistClient,
)
from src.todoist.services.todoist_task_service.task_card import TaskCard
from src.todoist.services.todoist_task_service.task_details import TaskDetails
from src.todoist.services.todoist_task_service.todoist_project_not_found_error import (
    TodoistProjectNotFoundError,
)

DUE_LANG = "ru"


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
        self,
        content: str,
        due: str | None = None,
        description: str | None = None,
        deadline: str | None = None,
        parent_id: str | None = None,
        project: str | None = None,
        labels: list[str] | None = None,
        create_project: bool = False,
    ) -> TaskCard:
        project_id = (
            self._project_id(project, create_project) if project is not None else None
        )
        task = self._client.add_task(
            content=content,
            labels=_merge_labels([ASSISTANT_LABEL], labels or []),
            due_string=due,
            due_lang=DUE_LANG if due else None,
            description=description,
            deadline_date=deadline,
            parent_id=parent_id,
            project_id=project_id,
        )
        return self._card(task, self._project_names())

    def read_task(self, task_id: str) -> TaskDetails:
        task = self._client.get_task(task_id)
        subtasks = self._client.list_subtasks(task_id)
        project_names = self._project_names()
        return TaskDetails(
            task=self._card(task, project_names),
            subtasks=[self._card(subtask, project_names) for subtask in subtasks],
            comments=self._client.list_comments(task_id),
        )

    def add_link(self, task_id: str, link: str) -> TodoistComment:
        return self._client.add_comment(task_id=task_id, content=link)

    def update_task(
        self,
        task_id: str,
        due: str | None = None,
        deadline: str | None = None,
        clear_deadline: bool = False,
        labels: list[str] | None = None,
    ) -> TaskCard:
        changes: dict[str, Any] = {}
        if due:
            changes["due_string"] = due
            changes["due_lang"] = DUE_LANG
        if clear_deadline:
            changes["deadline_date"] = None
        elif deadline:
            changes["deadline_date"] = deadline
        if labels:
            current = self._client.get_task(task_id).labels
            named = [label for label in labels if label != ASSISTANT_LABEL]
            changes["labels"] = _merge_labels(current, named)
        task = self._client.update_task(task_id, TodoistTaskUpdate(**changes))
        return self._card(task, self._project_names())

    def _project_id(self, name: str, create_project: bool) -> str:
        wanted = name.strip().casefold()
        for known in self._client.list_projects():
            if known.name.strip().casefold() == wanted:
                return known.id
        if not create_project:
            raise TodoistProjectNotFoundError(name)
        return self._client.add_project(name.strip()).id

    def _project_names(self) -> dict[str, str]:
        return {project.id: project.name for project in self._client.list_projects()}

    @staticmethod
    def _card(task: TodoistTask, project_names: dict[str, str]) -> TaskCard:
        return TaskCard(
            id=task.id,
            content=task.content,
            description=task.description,
            due=task.due,
            deadline=task.deadline,
            parent_id=task.parent_id,
            labels=task.labels,
            project=project_names.get(task.project_id, task.project_id),
            url=TASK_URL_TEMPLATE.format(task_id=task.id),
        )


def _merge_labels(base: list[str], extra: list[str]) -> list[str]:
    return list(dict.fromkeys([*base, *extra]))
