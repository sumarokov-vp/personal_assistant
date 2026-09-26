import asyncio
import os
import signal
import threading
from logging import getLogger

from claude_agent_sdk import ClaudeSDKClient

from src.agent.protocols.i_agent_options_factory import IAgentOptionsFactory

logger = getLogger(__name__)


class SDKClientPool:
    def __init__(self, options_factory: IAgentOptionsFactory) -> None:
        self._clients: dict[int, ClaudeSDKClient] = {}
        self._options_factory = options_factory
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def get_or_create(self, user_id: int) -> ClaudeSDKClient:
        if user_id not in self._clients:
            self._clients[user_id] = ClaudeSDKClient(self._options_factory.build())
        return self._clients[user_id]

    def remove(self, user_id: int) -> None:
        if user_id not in self._clients:
            return
        client = self._clients.pop(user_id)
        self._kill_subprocess(client)

    @staticmethod
    def _kill_subprocess(client: ClaudeSDKClient) -> None:
        transport = getattr(client, "_transport", None)
        if not transport:
            return
        process = getattr(transport, "_process", None)
        if not process or process.returncode is not None:
            return
        pid = process.pid
        logger.info("Killing CLI subprocess pid=%s", pid)
        os.kill(pid, signal.SIGKILL)
