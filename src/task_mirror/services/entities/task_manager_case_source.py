from pydantic import TypeAdapter

from src.cases.models.case_source import CaseSource
from src.task_manager.models.task_manager_identity import TaskManagerIdentity

CASE_SOURCES: TypeAdapter[CaseSource] = TypeAdapter(CaseSource)


class TaskManagerCaseSource:
    @staticmethod
    def of(manager: TaskManagerIdentity) -> CaseSource:
        return CASE_SOURCES.validate_python(manager.key)
