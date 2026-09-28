from src.conversations.errors.conversation_source_error import (
    ConversationSourceError,
)


class TelegramSessionRevokedError(ConversationSourceError):
    def __init__(self) -> None:
        super().__init__(
            "Сессия Telegram недействительна: владельцу нужно войти заново "
            "(uv run scripts/telegram_login.py) и перевыкатить бота"
        )
