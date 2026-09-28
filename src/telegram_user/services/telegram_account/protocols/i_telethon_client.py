from collections.abc import AsyncIterator
from datetime import datetime
from typing import Protocol

from telethon.tl.custom.dialog import Dialog
from telethon.tl.custom.message import Message
from telethon.tl.tlobject import TLRequest


class ITelethonClient(Protocol):
    async def connect(self) -> None: ...

    def is_connected(self) -> bool: ...

    async def is_user_authorized(self) -> bool: ...

    async def __call__(self, request: TLRequest) -> object: ...

    def iter_dialogs(self) -> AsyncIterator[Dialog]: ...

    def iter_messages(
        self,
        entity: object,
        limit: int,
        *,
        offset_date: datetime | None,
        search: str | None,
    ) -> AsyncIterator[Message]: ...

    async def get_messages(self, entity: object, *, ids: int) -> Message | None: ...

    async def download_media(
        self, message: Message, *, file: type[bytes]
    ) -> bytes | None: ...
