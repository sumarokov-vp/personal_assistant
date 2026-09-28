from src.conversations.errors.conversation_source_error import (
    ConversationSourceError,
)


class TelegramTimeoutError(ConversationSourceError):
    def __init__(self, seconds: float) -> None:
        super().__init__(f"Telegram не ответил за {seconds:g} с, повтори запрос позже")
        self.seconds = seconds
