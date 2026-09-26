from dataclasses import dataclass, field

from src.checkup.services.entities.created_checkup_task import CreatedCheckupTask

CHECKUP_RUN_CONTEXT_KEY = "checkup_run"


@dataclass
class CheckupRun:
    created: list[CreatedCheckupTask] = field(default_factory=list)

    def add_created(self, task: CreatedCheckupTask) -> None:
        self.created.append(task)

    def as_tool_context(self) -> dict[str, object]:
        return {CHECKUP_RUN_CONTEXT_KEY: self}
