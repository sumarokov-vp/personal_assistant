from typing import ClassVar

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, Field

from src.ai_tools.list_telegram_chats.protocols.i_conversation_directory import (
    IConversationDirectory,
)
from src.ai_tools.list_telegram_chats.protocols.i_untrusted_frame import (
    IUntrustedFrame,
)
from src.conversations.models.conversation_summary import ConversationSummary

MAX_LIMIT = 100


class ListTelegramChatsInput(BaseModel):
    title_contains: str | None = Field(
        default=None,
        description="Часть названия чата или имени собеседника. Пусто — все чаты",
    )
    limit: int = Field(
        default=20, ge=1, le=MAX_LIMIT, description="Сколько чатов вернуть"
    )


class ListTelegramChatsTool(BaseTool):
    name: ClassVar[str] = "list_telegram_chats"
    description: ClassVar[str] = (
        "Список чатов Telegram владельца (личные и группы, включая архивные; каналов нет), "
        "от недавних к старым: название, chat_id, личный или группа, дата последнего "
        "сообщения. Нужен, чтобы найти chat_id собеседника или группы для read_telegram "
        "и search_telegram."
    )
    Input: ClassVar[type[BaseModel]] = ListTelegramChatsInput

    def __init__(
        self, directory: IConversationDirectory, frame: IUntrustedFrame
    ) -> None:
        self._directory = directory
        self._frame = frame

    def execute(self, input: ListTelegramChatsInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        chats = self._directory.list_conversations(input.title_contains, input.limit)
        if not chats:
            return "Чатов Telegram не найдено."
        listing = "\n".join(_chat(chat) for chat in chats)
        return f"Чатов: {len(chats)}.\n{self._frame.wrap(listing)}"


def _chat(chat: ConversationSummary) -> str:
    kind = "группа" if chat.is_group else "личный"
    return (
        f"chat_id {chat.conversation_id} · {chat.title} · {kind} · "
        f"последнее {chat.last_message_date}"
    )
