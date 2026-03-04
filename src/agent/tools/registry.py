from dataclasses import dataclass

from bot_framework import IDocumentSender


@dataclass
class SessionContext:
    chat_id: int
    document_sender: IDocumentSender


class SessionRegistry:
    def __init__(self) -> None:
        self._sessions: dict[int, SessionContext] = {}
        self._current_user_id: int | None = None

    def set_context(self, user_id: int, chat_id: int, document_sender: IDocumentSender) -> None:
        self._sessions[user_id] = SessionContext(chat_id=chat_id, document_sender=document_sender)
        self._current_user_id = user_id

    def get_context(self, user_id: int) -> SessionContext:
        return self._sessions[user_id]

    def get_current_context(self) -> SessionContext:
        if self._current_user_id is None:
            raise ValueError("No active session context")
        return self._sessions[self._current_user_id]
