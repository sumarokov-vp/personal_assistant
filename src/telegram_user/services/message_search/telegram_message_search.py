from collections.abc import AsyncIterator
from datetime import datetime

from telethon.tl.custom.message import Message

from src.conversations.models.message_query import MessageQuery
from src.conversations.models.message_summary import MessageSummary
from src.telegram_user.errors.telegram_search_query_error import (
    TelegramSearchQueryError,
)
from src.telegram_user.models.telegram_chat import TelegramChat
from src.telegram_user.services.entities.chat_profile import public_username
from src.telegram_user.services.message_search.protocols.i_owner_moments import (
    IOwnerMoments,
)
from src.telegram_user.services.message_search.protocols.i_searchable_account import (
    ISearchableAccount,
)
from src.telegram_user.services.message_search.protocols.i_summary_mapper import (
    ISummaryMapper,
)

MAX_SCANNED_MESSAGES = 1000
MAX_PARTICIPANT_CHATS = 5

type Found = tuple[TelegramChat, Message]


class TelegramMessageSearch:
    def __init__(
        self,
        account: ISearchableAccount,
        mapper: ISummaryMapper,
        clock: IOwnerMoments,
    ) -> None:
        self._account = account
        self._mapper = mapper
        self._clock = clock

    async def search(self, query: MessageQuery) -> list[MessageSummary]:
        text = query.text.strip()
        participant = (query.participant or "").strip().casefold()
        since = self._clock.aware(query.since)
        until = self._clock.aware(query.until)
        scan = MAX_SCANNED_MESSAGES if participant else query.limit
        if query.conversation_id is not None:
            chat = await self._account.chat(query.conversation_id)
            found = await self._collect(
                self._in_chat(chat, text, until, scan), since, participant, query.limit
            )
        elif text:
            found = await self._collect(
                self._account.global_search(text, until, scan),
                since,
                participant,
                query.limit,
            )
        elif participant:
            found = await self._in_chats_named(participant, since, until, query.limit)
        else:
            raise TelegramSearchQueryError()
        return [self._mapper.to_summary(chat, message) for chat, message in found]

    async def _in_chats_named(
        self,
        participant: str,
        since: datetime | None,
        until: datetime | None,
        limit: int,
    ) -> list[Found]:
        chats = [
            chat
            async for chat in self._account.chats()
            if participant in chat.title.casefold()
        ][:MAX_PARTICIPANT_CHATS]
        found: list[Found] = []
        for chat in chats:
            found += await self._collect(
                self._in_chat(chat, "", until, limit), since, "", limit
            )
        found.sort(key=lambda item: item[1].date, reverse=True)
        return found[:limit]

    async def _in_chat(
        self, chat: TelegramChat, text: str, until: datetime | None, scan: int
    ) -> AsyncIterator[Found]:
        async for message in self._account.history(chat, text, until, scan):
            yield chat, message

    async def _collect(
        self,
        candidates: AsyncIterator[Found],
        since: datetime | None,
        participant: str,
        limit: int,
    ) -> list[Found]:
        found: list[Found] = []
        scanned = 0
        async for chat, message in candidates:
            scanned += 1
            if since is not None and message.date < since:
                break
            if not participant or self._involves(participant, chat, message):
                found.append((chat, message))
            if len(found) >= limit or scanned >= MAX_SCANNED_MESSAGES:
                break
        return found

    def _involves(self, participant: str, chat: TelegramChat, message: Message) -> bool:
        names = (
            chat.title,
            self._mapper.sender(chat, message),
            public_username(message.sender) or "",
        )
        return any(participant in name.casefold() for name in names)
