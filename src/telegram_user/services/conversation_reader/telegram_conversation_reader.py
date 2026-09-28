from telethon.tl.custom.message import Message

from src.conversations.models.conversation import Conversation
from src.conversations.models.conversation_message import ConversationMessage
from src.conversations.models.conversation_window import ConversationWindow
from src.telegram_user.services.conversation_reader.protocols.i_chat_history import (
    IChatHistory,
)
from src.telegram_user.services.conversation_reader.protocols.i_message_locator import (
    IMessageLocator,
)
from src.telegram_user.services.conversation_reader.protocols.i_message_mapper import (
    IMessageMapper,
)
from src.telegram_user.services.conversation_reader.protocols.i_owner_moments import (
    IOwnerMoments,
)


class TelegramConversationReader:
    def __init__(
        self,
        account: IChatHistory,
        locator: IMessageLocator,
        mapper: IMessageMapper,
        clock: IOwnerMoments,
    ) -> None:
        self._account = account
        self._locator = locator
        self._mapper = mapper
        self._clock = clock

    async def read_message(self, message_id: str) -> ConversationMessage:
        chat, message = await self._locator.locate(message_id)
        return self._mapper.to_message(chat, message)

    async def read_conversation(
        self, conversation_id: str, window: ConversationWindow
    ) -> Conversation:
        chat = await self._account.chat(conversation_id)
        since = self._clock.aware(window.since)
        newest_first: list[Message] = []
        has_earlier = False
        async for message in self._account.history(
            chat, None, self._clock.aware(window.until), window.limit + 1
        ):
            if (since is not None and message.date < since) or len(
                newest_first
            ) >= window.limit:
                has_earlier = True
                break
            newest_first.append(message)
        return Conversation(
            conversation_id=chat.conversation_id,
            title=chat.title,
            is_group=chat.is_group,
            messages=[
                self._mapper.to_message(chat, message)
                for message in reversed(newest_first)
            ],
            has_earlier=has_earlier,
        )
