from datetime import date
from threading import Lock

from src.cases.models.case_event import CaseEvent
from src.cases.models.case_source import CaseSource
from src.cases.models.case_task import CaseTask
from src.cases.models.task_change import TaskChange
from src.task_manager.models.new_managed_task import NewManagedTask
from src.task_mirror.services.outbound_mirror.protocols.i_mirror_link_recorder import (
    IMirrorLinkRecorder,
)
from src.task_mirror.services.outbound_mirror.protocols.i_mirror_task_writer import (
    IMirrorTaskWriter,
)

SELF_ASSIGNEE = "self"
OWNER_SOURCE = "owner"
MIRRORED_SUMMARY = "Задача отражена в {manager}"


class OutboundMirror:
    def __init__(self, tasks: IMirrorTaskWriter, cases: IMirrorLinkRecorder) -> None:
        self._tasks = tasks
        self._cases = cases
        self._lock = Lock()
        self._created: dict[str, str] = {}
        self._linked: set[str] = set()

    def task_recorded(self, event: CaseEvent) -> None:
        state = event.task
        if state is None or state.assignee != SELF_ASSIGNEE:
            return
        if state.external_id is None and state.status == "open":
            self.mirror(event.id, event.summary, state.due)

    def task_changed(self, task: CaseTask) -> None:
        if task.assignee != SELF_ASSIGNEE or task.status != "open":
            return
        if task.external_id is not None and self._tasks.identity.owns(task.external_id):
            self._tasks.set_deadline(task.external_id, task.due)
        elif task.external_id is None:
            self.mirror(task.id, task.summary, task.due)

    def task_closed(self, task: CaseTask, closed_by: CaseSource) -> None:
        if closed_by != OWNER_SOURCE or task.assignee != SELF_ASSIGNEE:
            return
        if task.external_id is not None and self._tasks.identity.owns(task.external_id):
            self._tasks.close_task(task.external_id)

    def mirror(self, task_id: str, summary: str, due: date | None) -> None:
        with self._lock:
            if task_id in self._linked:
                return
            ref = self._created.get(task_id)
            if ref is None:
                ref = self._tasks.add_task(
                    NewManagedTask(title=summary, deadline=due)
                ).ref
                self._created[task_id] = ref
            self._cases.update_task(
                task_id,
                TaskChange(
                    external_id=ref,
                    source="assistant",
                    summary=MIRRORED_SUMMARY.format(manager=self._tasks.identity.title),
                ),
            )
            self._linked.add(task_id)
