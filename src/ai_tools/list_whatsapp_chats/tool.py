from typing import ClassVar

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, Field

from src.ai_tools.list_whatsapp_chats.protocols.i_conversation_directory import (
    IConversationDirectory,
)
from src.ai_tools.list_whatsapp_chats.protocols.i_freshness_note import (
    IFreshnessNote,
)
from src.ai_tools.list_whatsapp_chats.protocols.i_untrusted_frame import (
    IUntrustedFrame,
)
from src.conversations.models.conversation_summary import ConversationSummary

MAX_LIMIT = 100


class ListWhatsAppChatsInput(BaseModel):
    title_contains: str | None = Field(
        default=None,
        description="Часть названия чата или имени собеседника. Пусто — все чаты",
    )
    limit: int = Field(
        default=20, ge=1, le=MAX_LIMIT, description="Сколько чатов вернуть"
    )


class ListWhatsAppChatsTool(BaseTool):
    name: ClassVar[str] = "list_whatsapp_chats"
    description: ClassVar[str] = (
        "Список чатов WhatsApp владельца, от недавних к старым: название, chat_id, личный "
        "или группа, дата последнего сообщения. Нужен, чтобы найти chat_id собеседника "
        "для read_whatsapp. В начале ответа — дата последнего сообщения в снимке WhatsApp."
    )
    Input: ClassVar[type[BaseModel]] = ListWhatsAppChatsInput

    def __init__(
        self,
        directory: IConversationDirectory,
        freshness: IFreshnessNote,
        frame: IUntrustedFrame,
    ) -> None:
        self._directory = directory
        self._freshness = freshness
        self._frame = frame

    def execute(self, input: ListWhatsAppChatsInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        chats = self._directory.list_conversations(input.title_contains, input.limit)
        note = self._freshness.note()
        if not chats:
            return f"{note}\nЧатов WhatsApp не найдено."
        listing = "\n".join(_chat(chat) for chat in chats)
        return f"{note}\nЧатов: {len(chats)}.\n{self._frame.wrap(listing)}"


def _chat(chat: ConversationSummary) -> str:
    kind = "группа" if chat.is_group else "личный"
    return (
        f"chat_id {chat.conversation_id} · {chat.title} · {kind} · "
        f"последнее {chat.last_message_date}"
    )
