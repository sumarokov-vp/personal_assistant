from typing import Protocol

from telethon.tl.custom.message import Message


class IMediaDownload(Protocol):
    async def download(self, message: Message) -> bytes | None: ...
