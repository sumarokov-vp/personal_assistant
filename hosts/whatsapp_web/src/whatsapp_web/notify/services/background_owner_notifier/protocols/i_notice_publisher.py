from typing import Protocol


class INoticePublisher(Protocol):
    async def publish(self, text: str) -> None: ...
