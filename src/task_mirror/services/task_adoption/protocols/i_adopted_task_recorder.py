from typing import Protocol

from src.cases.models.case_task import CaseTask
from src.cases.models.event_addition import EventAddition
from src.cases.models.new_event import NewEvent
from src.cases.models.task_query import TaskQuery


class IAdoptedTaskRecorder(Protocol):
    def list_tasks(self, query: TaskQuery) -> list[CaseTask]: ...

    def add_event(self, case_id: str, event: NewEvent) -> EventAddition: ...
