from src.conversations.errors.conversation_source_error import (
    ConversationSourceError,
)


class TelegramFloodWaitError(ConversationSourceError):
    def __init__(self, seconds: int) -> None:
        super().__init__(f"Telegram ограничил запросы, повтори через {seconds} с")
        self.seconds = seconds
