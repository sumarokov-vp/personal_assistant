from typing import Protocol

from src.dropbox.services.move_executor.move_plan_execution import MovePlanExecution


class IExecutionCardUpdater(Protocol):
    def show_execution(
        self, chat_id: int, message_id: int, execution: MovePlanExecution
    ) -> None: ...
