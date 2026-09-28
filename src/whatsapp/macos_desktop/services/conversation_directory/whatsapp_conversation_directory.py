from src.conversations.models.conversation_summary import ConversationSummary
from src.whatsapp.macos_desktop.services.conversation_directory.protocols.i_chat_listing import (
    IChatListing,
)
from src.whatsapp.macos_desktop.services.conversation_directory.protocols.i_date_display import (
    IDateDisplay,
)
from src.whatsapp.macos_desktop.services.entities.chat_title import (
    chat_title,
    is_group_session,
)


class WhatsAppConversationDirectory:
    def __init__(self, chats: IChatListing, dates: IDateDisplay) -> None:
        self._chats = chats
        self._dates = dates

    def list_conversations(
        self, title_contains: str | None, limit: int
    ) -> list[ConversationSummary]:
        title = (title_contains or "").strip()
        return [
            ConversationSummary(
                conversation_id=str(chat.chat_pk),
                title=chat_title(chat.title, chat.jid, chat.chat_pk),
                is_group=is_group_session(chat.session_type),
                last_message_date=self._dates.display(chat.last_message_at),
            )
            for chat in self._chats.list_chats(title or None, limit)
        ]
