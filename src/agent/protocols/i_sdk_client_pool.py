import asyncio
from typing import Protocol

from claude_agent_sdk import ClaudeSDKClient


class ISDKClientPool(Protocol):
    @property
    def loop(self) -> asyncio.AbstractEventLoop: ...

    def get_or_create(self, user_id: int) -> ClaudeSDKClient: ...

    def remove(self, user_id: int) -> None: ...
