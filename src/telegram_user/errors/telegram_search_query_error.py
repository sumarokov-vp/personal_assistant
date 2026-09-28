from src.conversations.errors.conversation_source_error import (
    ConversationSourceError,
)


class TelegramSearchQueryError(ConversationSourceError):
    def __init__(self) -> None:
        super().__init__(
            "Поиск по всему Telegram идёт по тексту: задай text, "
            "либо participant (имя чата), либо conversation_id"
        )
