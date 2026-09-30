from src.cases.models.case_event import CaseEvent
from src.cases.models.case_task import CaseTask
from src.cases.models.task_closure import TaskClosure


class RecordingListener:
    def __init__(self) -> None:
        self.recorded: list[tuple[str, CaseEvent]] = []
        self.changed: list[CaseTask] = []
        self.closed: list[CaseTask] = []
        self.closures: list[TaskClosure] = []

    def task_recorded(self, case_id: str, task: CaseEvent) -> None:
        self.recorded.append((case_id, task))

    def task_changed(self, task: CaseTask) -> None:
        self.changed.append(task)

    def task_closed(self, task: CaseTask, closure: TaskClosure) -> None:
        self.closed.append(task)
        self.closures.append(closure)
