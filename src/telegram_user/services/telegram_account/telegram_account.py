import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime

from telethon.errors import FloodPremiumWaitError, FloodWaitError
from telethon.tl.custom.message import Message
from telethon.tl.functions.account import UpdateStatusRequest

from src.conversations.errors.conversation_not_found_error import (
    ConversationNotFoundError,
)
from src.telegram_user.errors.telegram_flood_wait_error import TelegramFloodWaitError
from src.telegram_user.errors.telegram_session_revoked_error import (
    TelegramSessionRevokedError,
)
from src.telegram_user.models.telegram_chat import TelegramChat
from src.telegram_user.services.entities.chat_profile import chat_from_entity
from src.telegram_user.services.telegram_account.protocols.i_telethon_client import (
    ITelethonClient,
)
from src.telegram_user.services.telegram_account.protocols.i_telethon_client_factory import (
    ITelethonClientFactory,
)

logger = logging.getLogger(__name__)

FLOOD_ERRORS = (FloodWaitError, FloodPremiumWaitError)


class TelegramAccount:
    def __init__(self, client_factory: ITelethonClientFactory) -> None:
        self._client_factory = client_factory
        self._client: ITelethonClient | None = None
        self._chats: dict[str, TelegramChat] = {}
        self._connecting = asyncio.Lock()

    async def perform[T](self, work: Callable[[], Awaitable[T]]) -> T:
        client = await self._connected()
        try:
            return await work()
        except FLOOD_ERRORS as error:
            raise TelegramFloodWaitError(error.seconds) from error
        finally:
            await self._stay_offline(client)

    async def chats(self) -> AsyncIterator[TelegramChat]:
        async for dialog in self._current_client().iter_dialogs():
            chat = chat_from_entity(dialog.entity, dialog.date)
            if chat is None:
                continue
            self._chats[chat.conversation_id] = chat
            yield chat

    async def find_chat(self, conversation_id: str) -> TelegramChat | None:
        wanted = conversation_id.strip()
        known = self._chats.get(wanted)
        if known is not None:
            return known
        async for chat in self.chats():
            if chat.conversation_id == wanted:
                return chat
        return None

    async def chat(self, conversation_id: str) -> TelegramChat:
        chat = await self.find_chat(conversation_id)
        if chat is None:
            raise ConversationNotFoundError(conversation_id)
        return chat

    async def history(
        self,
        chat: TelegramChat,
        search: str | None,
        until: datetime | None,
        limit: int,
    ) -> AsyncIterator[Message]:
        messages = self._current_client().iter_messages(
            chat.entity, limit, offset_date=until, search=search or None
        )
        async for message in messages:
            if message.action is None:
                yield message

    async def global_search(
        self, text: str, until: datetime | None, limit: int
    ) -> AsyncIterator[tuple[TelegramChat, Message]]:
        messages = self._current_client().iter_messages(
            None, limit, offset_date=until, search=text
        )
        async for message in messages:
            chat = chat_from_entity(message.chat)
            if chat is None or message.action is not None:
                continue
            self._chats.setdefault(chat.conversation_id, chat)
            yield self._chats[chat.conversation_id], message

    async def message(self, chat: TelegramChat, number: int) -> Message | None:
        message = await self._current_client().get_messages(chat.entity, ids=number)
        if message is None or message.action is not None:
            return None
        return message

    async def download(self, message: Message) -> bytes | None:
        return await self._current_client().download_media(message, file=bytes)

    async def _connected(self) -> ITelethonClient:
        async with self._connecting:
            if self._client is None:
                self._client = self._client_factory.create()
            client = self._client
            if not client.is_connected():
                await client.connect()
                if not await client.is_user_authorized():
                    raise TelegramSessionRevokedError()
            return client

    async def _stay_offline(self, client: ITelethonClient) -> None:
        if not client.is_connected():
            return
        try:
            await client(UpdateStatusRequest(offline=True))
        except FLOOD_ERRORS as error:
            logger.warning(
                "Telegram offline status skipped: flood wait %s s", error.seconds
            )

    def _current_client(self) -> ITelethonClient:
        if self._client is None:
            raise RuntimeError("TelegramAccount: запрос к Telegram вне perform")
        return self._client
