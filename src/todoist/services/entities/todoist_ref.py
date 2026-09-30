from src.task_manager.errors.foreign_task_ref_error import ForeignTaskRefError
from src.todoist.services.entities.todoist_identity import TODOIST_IDENTITY


class TodoistRef:
    @staticmethod
    def of(task_id: str) -> str:
        return TODOIST_IDENTITY.ref(task_id)

    @staticmethod
    def task_id(ref: str) -> str:
        task_id = TODOIST_IDENTITY.native_id(ref)
        if task_id is None:
            raise ForeignTaskRefError(ref, TODOIST_IDENTITY.title)
        return task_id
