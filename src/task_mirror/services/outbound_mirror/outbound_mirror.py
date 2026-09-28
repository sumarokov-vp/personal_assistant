from datetime import date
from threading import Lock

from src.cases.models.case_event import CaseEvent
from src.cases.models.case_task import CaseTask
from src.cases.models.task_change import TaskChange
from src.task_mirror.models.todoist_external_id import TodoistExternalId
from src.task_mirror.services.outbound_mirror.protocols.i_mirror_link_recorder import (
    IMirrorLinkRecorder,
)
from src.task_mirror.services.outbound_mirror.protocols.i_todoist_task_writer import (
    ITodoistTaskWriter,
)
from src.todoist.models.todoist_task_update import TodoistTaskUpdate

SELF_ASSIGNEE = "self"
ASSISTANT_LABEL = "pa"
MIRRORED_SUMMARY = "Задача отражена в Todoist"


class TodoistOutboundMirror:
    def __init__(self, todoist: ITodoistTaskWriter, cases: IMirrorLinkRecorder) -> None:
        self._todoist = todoist
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
        todoist_task_id = TodoistExternalId.todoist_task_id(task.external_id)
        if todoist_task_id is not None:
            self._todoist.update_task(
                todoist_task_id, TodoistTaskUpdate(deadline_date=_iso(task.due))
            )
        elif task.external_id is None:
            self.mirror(task.id, task.summary, task.due)

    def mirror(self, task_id: str, summary: str, due: date | None) -> None:
        with self._lock:
            if task_id in self._linked:
                return
            todoist_task_id = self._created.get(task_id)
            if todoist_task_id is None:
                created = self._todoist.add_task(
                    content=summary,
                    labels=[ASSISTANT_LABEL],
                    deadline_date=_iso(due),
                )
                todoist_task_id = created.id
                self._created[task_id] = todoist_task_id
            self._cases.update_task(
                task_id,
                TaskChange(
                    external_id=TodoistExternalId.of(todoist_task_id),
                    source="assistant",
                    summary=MIRRORED_SUMMARY,
                ),
            )
            self._linked.add(task_id)


def _iso(due: date | None) -> str | None:
    return due.isoformat() if due is not None else None
