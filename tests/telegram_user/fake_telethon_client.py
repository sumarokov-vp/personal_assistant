from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import datetime

from telethon import utils
from telethon.errors import FloodWaitError
from telethon.tl.custom.message import Message
from telethon.tl.tlobject import TLRequest
from telethon.tl.types import Message as RawMessage
from telethon.tl.types import TypeMessageMedia


@dataclass(frozen=True)
class FakeDialog:
    entity: object
    date: datetime


class NoEntityCache:
    def get(self, entity_id: int) -> None:
        return None


class FakeTelethonClient:
    def __init__(self, owner_id: int) -> None:
        self._self_id = owner_id
        self._mb_entity_cache = NoEntityCache()
        self._entities: dict[int, object] = {}
        self._dialogs: list[FakeDialog] = []
        self._messages: list[Message] = []
        self._media: dict[tuple[int, int], bytes] = {}
        self.requests: list[TLRequest] = []
        self.unexpected_calls: list[str] = []
        self.requested_limits: list[int] = []
        self.connected = False
        self.connects = 0
        self.authorized = True
        self.flood_seconds: int | None = None

    def add_chat(self, entity: object, last_message_at: datetime) -> None:
        self.add_entity(entity)
        self._dialogs.append(FakeDialog(entity, last_message_at))

    def add_entity(self, entity: object) -> None:
        self._entities[utils.get_peer_id(entity)] = entity

    def add_message(
        self,
        chat: object,
        number: int,
        date: datetime,
        text: str,
        sender: object | None = None,
        out: bool = False,
        media: TypeMessageMedia | None = None,
        content: bytes | None = None,
    ) -> Message:
        message = RawMessage(
            id=number,
            peer_id=utils.get_peer(chat),
            date=date,
            message=text,
            out=out,
            from_id=None if sender is None else utils.get_peer(sender),
            media=media,
        )
        message._finish_init(self, self._entities, None)
        self._messages.append(message)
        if content is not None:
            self._media[(message.chat_id, number)] = content
        return message

    async def connect(self) -> None:
        self.connected = True
        self.connects += 1

    def is_connected(self) -> bool:
        return self.connected

    async def is_user_authorized(self) -> bool:
        return self.authorized

    async def __call__(self, request: TLRequest) -> object:
        self.requests.append(request)
        return True

    async def iter_dialogs(self) -> AsyncIterator[FakeDialog]:
        for dialog in sorted(self._dialogs, key=lambda item: item.date, reverse=True):
            yield dialog

    async def iter_messages(
        self,
        entity: object,
        limit: int,
        *,
        offset_date: datetime | None,
        search: str | None,
    ) -> AsyncIterator[Message]:
        if self.flood_seconds is not None:
            raise FloodWaitError(request=None, capture=self.flood_seconds)
        peer_id = None if entity is None else utils.get_peer_id(entity)
        matching = [
            message
            for message in self._messages
            if (peer_id is None or message.chat_id == peer_id)
            and (offset_date is None or message.date < offset_date)
            and (not search or search.casefold() in message.message.casefold())
        ]
        self.requested_limits.append(limit)
        for message in sorted(
            matching, key=lambda item: (item.date, item.id), reverse=True
        )[:limit]:
            yield message

    async def get_messages(self, entity: object, *, ids: int) -> Message | None:
        peer_id = utils.get_peer_id(entity)
        return next(
            (
                message
                for message in self._messages
                if message.chat_id == peer_id and message.id == ids
            ),
            None,
        )

    async def download_media(
        self, message: Message, *, file: type[bytes]
    ) -> bytes | None:
        return self._media.get((message.chat_id, message.id))

    def __getattr__(self, name: str) -> Callable[..., None]:
        self.unexpected_calls.append(name)
        return lambda *args, **kwargs: None


class FakeTelethonClientFactory:
    def __init__(self, client: FakeTelethonClient) -> None:
        self._client = client
        self.created = 0

    def create(self) -> FakeTelethonClient:
        self.created += 1
        return self._client
