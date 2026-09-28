from logging import getLogger

from pydantic import ValidationError

from src.cases.errors.cases_service_error import CasesServiceError
from src.cases.models.case_event import CaseEvent
from src.cases.models.case_task import CaseTask
from src.task_mirror.services.outbound_mirror.outbound_mirror import (
    TodoistOutboundMirror,
)
from src.todoist.repos.todoist_error import TodoistError

logger = getLogger(__name__)


class TaskMirrorListener:
    def __init__(self, mirror: TodoistOutboundMirror) -> None:
        self._mirror = mirror

    def task_recorded(self, case_id: str, task: CaseEvent) -> None:  # noqa: ARG002
        try:
            self._mirror.task_recorded(task)
        except (TodoistError, CasesServiceError, ValidationError) as error:
            logger.warning("Todoist mirror of task %s postponed: %s", task.id, error)

    def task_changed(self, task: CaseTask) -> None:
        try:
            self._mirror.task_changed(task)
        except (TodoistError, CasesServiceError, ValidationError) as error:
            logger.warning("Todoist mirror of task %s postponed: %s", task.id, error)
