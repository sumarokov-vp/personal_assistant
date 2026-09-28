from datetime import datetime
from typing import Protocol


class IClock(Protocol):
    def now(self) -> datetime: ...

    async def sleep(self, seconds: float) -> None: ...
