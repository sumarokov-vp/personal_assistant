from typing import Protocol

from src.cases.models.case_task import CaseTask
from src.cases.models.task_query import TaskQuery


class ITaskLister(Protocol):
    def list_tasks(self, query: TaskQuery) -> list[CaseTask]: ...
