from typing import Any, Protocol

from ai_framework import AIResponse, Attachment


class IConversationAI(Protocol):
    def update_system_prompt(self, text: str) -> None: ...

    def process_message(
        self,
        thread_id: str,
        user_message: str,
        tool_context: dict[str, Any] | None = None,
        attachments: list[Attachment] | None = None,
    ) -> AIResponse: ...
