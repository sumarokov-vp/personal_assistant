from telethon.tl.custom.message import Message

from src.conversations.errors.message_not_found_error import MessageNotFoundError
from src.telegram_user.models.telegram_chat import TelegramChat
from src.telegram_user.services.entities.message_key import parse_message_key
from src.telegram_user.services.message_locator.protocols.i_chat_messages import (
    IChatMessages,
)


class MessageLocator:
    def __init__(self, account: IChatMessages) -> None:
        self._account = account

    async def locate(self, message_id: str) -> tuple[TelegramChat, Message]:
        key = parse_message_key(message_id)
        if key is None:
            raise MessageNotFoundError(message_id)
        conversation_id, number = key
        chat = await self._account.find_chat(conversation_id)
        message = None if chat is None else await self._account.message(chat, number)
        if chat is None or message is None:
            raise MessageNotFoundError(message_id)
        return chat, message
