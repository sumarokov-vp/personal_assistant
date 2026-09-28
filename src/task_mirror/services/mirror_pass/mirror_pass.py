from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from src.cases.models.task_query import TaskQuery
from src.task_mirror.services.mirror_pass.protocols.i_inbound_sync import IInboundSync
from src.task_mirror.services.mirror_pass.protocols.i_open_task_lister import (
    IOpenTaskLister,
)
from src.task_mirror.services.mirror_pass.protocols.i_task_mirror import ITaskMirror

INITIAL_LOOKBACK = timedelta(days=1)
PASS_OVERLAP = timedelta(minutes=2)
OPEN_TASKS_LIMIT = 1000
SELF_ASSIGNEE = "self"


class TodoistMirrorPass:
    def __init__(
        self,
        outbound: ITaskMirror,
        inbound: IInboundSync,
        tasks: IOpenTaskLister,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._outbound = outbound
        self._inbound = inbound
        self._tasks = tasks
        self._now = now
        self._since = now() - INITIAL_LOOKBACK

    def run(self) -> None:
        started = self._now()
        self._mirror_unlinked()
        self._inbound.sync(self._since)
        self._since = started - PASS_OVERLAP

    def _mirror_unlinked(self) -> None:
        open_tasks = self._tasks.list_tasks(
            TaskQuery(status="open", assignee=SELF_ASSIGNEE, limit=OPEN_TASKS_LIMIT)
        )
        for task in open_tasks:
            if task.external_id is None:
                self._outbound.mirror(task.id, task.summary, task.due)
