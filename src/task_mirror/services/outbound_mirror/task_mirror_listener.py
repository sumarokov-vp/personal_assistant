from logging import getLogger

from pydantic import ValidationError

from src.cases.errors.cases_service_error import CasesServiceError
from src.cases.models.case_event import CaseEvent
from src.cases.models.case_task import CaseTask
from src.cases.models.task_closure import TaskClosure
from src.task_manager.errors.task_manager_error import TaskManagerError
from src.task_mirror.services.outbound_mirror.outbound_mirror import OutboundMirror

logger = getLogger(__name__)


class TaskMirrorListener:
    def __init__(self, mirror: OutboundMirror) -> None:
        self._mirror = mirror

    def task_recorded(self, case_id: str, task: CaseEvent) -> None:  # noqa: ARG002
        try:
            self._mirror.task_recorded(task)
        except (TaskManagerError, CasesServiceError, ValidationError) as error:
            logger.warning("Task mirror of task %s postponed: %s", task.id, error)

    def task_changed(self, task: CaseTask) -> None:
        try:
            self._mirror.task_changed(task)
        except (TaskManagerError, CasesServiceError, ValidationError) as error:
            logger.warning("Task mirror of task %s postponed: %s", task.id, error)

    def task_closed(self, task: CaseTask, closure: TaskClosure) -> None:
        try:
            self._mirror.task_closed(task, closure.source)
        except (TaskManagerError, CasesServiceError, ValidationError) as error:
            logger.warning("Closing task %s in task manager failed: %s", task.id, error)
