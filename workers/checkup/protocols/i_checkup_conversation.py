from typing import Any, Protocol

from workers.checkup.protocols.i_checkup_answer import ICheckupAnswer


class ICheckupConversation(Protocol):
    def process_message(
        self,
        thread_id: str,
        user_message: str,
        tool_context: dict[str, Any] | None = None,
    ) -> ICheckupAnswer: ...
