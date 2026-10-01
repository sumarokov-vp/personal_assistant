from typing import Any, Protocol

from workers.scheduled_run.protocols.i_run_answer import IRunAnswer


class IRunConversation(Protocol):
    def update_system_prompt(self, text: str) -> None: ...

    def process_message(
        self,
        thread_id: str,
        user_message: str,
        tool_context: dict[str, Any] | None = None,
    ) -> IRunAnswer: ...
