from dataclasses import dataclass

import telebot


@dataclass
class SessionContext:
    chat_id: int
    bot: telebot.TeleBot


class SessionRegistry:
    def __init__(self) -> None:
        self._sessions: dict[int, SessionContext] = {}
        self._current_user_id: int | None = None

    def set_context(self, user_id: int, chat_id: int, bot: telebot.TeleBot) -> None:
        self._sessions[user_id] = SessionContext(chat_id=chat_id, bot=bot)
        self._current_user_id = user_id

    def get_context(self, user_id: int) -> SessionContext:
        return self._sessions[user_id]

    def get_current_context(self) -> SessionContext:
        if self._current_user_id is None:
            raise ValueError("No active session context")
        return self._sessions[self._current_user_id]
