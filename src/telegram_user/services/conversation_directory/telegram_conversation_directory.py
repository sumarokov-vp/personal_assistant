from src.conversations.models.conversation_summary import ConversationSummary
from src.telegram_user.services.conversation_directory.protocols.i_chat_listing import (
    IChatListing,
)
from src.telegram_user.services.conversation_directory.protocols.i_date_display import (
    IDateDisplay,
)


class TelegramConversationDirectory:
    def __init__(self, account: IChatListing, dates: IDateDisplay) -> None:
        self._account = account
        self._dates = dates

    async def list_conversations(
        self, title_contains: str | None, limit: int
    ) -> list[ConversationSummary]:
        needle = (title_contains or "").strip().casefold()
        found: list[ConversationSummary] = []
        async for chat in self._account.chats():
            if needle and needle not in chat.title.casefold():
                continue
            found.append(
                ConversationSummary(
                    conversation_id=chat.conversation_id,
                    title=chat.title,
                    is_group=chat.is_group,
                    last_message_date=self._dates.display(chat.last_message_at),
                )
            )
            if len(found) >= limit:
                break
        return found
