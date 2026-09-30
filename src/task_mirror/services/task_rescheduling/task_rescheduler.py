from collections.abc import Callable
from datetime import UTC, date, datetime

from src.cases.models.case_source import CaseSource
from src.cases.models.case_task import CaseTask
from src.cases.models.new_event import NewEvent
from src.task_mirror.errors.closed_task_move_error import ClosedTaskMoveError
from src.task_mirror.errors.recurring_task_move_error import RecurringTaskMoveError
from src.task_mirror.errors.task_not_in_manager_error import TaskNotInManagerError
from src.task_mirror.services.task_rescheduling.protocols.i_planned_task_reader import (
    IPlannedTaskReader,
)
from src.task_mirror.services.task_rescheduling.protocols.i_planned_task_writer import (
    IPlannedTaskWriter,
)
from src.task_mirror.services.task_rescheduling.protocols.i_reschedule_note_recorder import (
    IRescheduleNoteRecorder,
)

SELF_ASSIGNEE = "self"
RESCHEDULED_NOTE = "«{task}» — дата выполнения в {manager}: {planned}. {reason}"


class TaskRescheduler:
    def __init__(
        self,
        reader: IPlannedTaskReader,
        writer: IPlannedTaskWriter,
        cases: IRescheduleNoteRecorder,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._cases = cases
        self._now = now

    def reschedule(
        self, task: CaseTask, planned: date, reason: str, source: CaseSource
    ) -> None:
        manager = self._writer.identity.title
        ref = task.external_id
        if (
            ref is None
            or task.assignee != SELF_ASSIGNEE
            or not self._writer.identity.owns(ref)
        ):
            raise TaskNotInManagerError(task.id, manager)
        if task.status != "open":
            raise ClosedTaskMoveError(task.id, task.status)
        if self._reader.get_task(ref).recurring:
            raise RecurringTaskMoveError(task.id, manager)
        self._writer.set_due(ref, planned)
        self._cases.add_event(
            task.case.id,
            NewEvent(
                occurred_at=self._now(),
                source=source,
                kind="note",
                summary=RESCHEDULED_NOTE.format(
                    task=task.summary,
                    manager=manager,
                    planned=planned.strftime("%d.%m.%Y"),
                    reason=reason,
                ),
            ),
        )
