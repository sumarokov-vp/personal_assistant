import asyncio
import os
import signal
import threading
from logging import getLogger
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

logger = getLogger(__name__)


class SDKClientPool:
    def __init__(self, mcp_server: Any | None = None) -> None:
        self._clients: dict[int, ClaudeSDKClient] = {}
        self._mcp_server = mcp_server
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def get_or_create(self, user_id: int) -> ClaudeSDKClient:
        if user_id not in self._clients:
            options = ClaudeAgentOptions(
                cwd=str(Path.home()),
                permission_mode="bypassPermissions",
                system_prompt={"type": "preset", "preset": "claude_code"},
                tools={"type": "preset", "preset": "claude_code"},
                settings='{"enabledPlugins": {}}',
                setting_sources=["user", "project", "local"],
                stderr=lambda line: logger.debug("CLI stderr: %s", line),
            )
            if self._mcp_server is not None:
                options.mcp_servers = {"bot-tools": self._mcp_server}
                options.allowed_tools = ["mcp__bot-tools__*"]
            self._clients[user_id] = ClaudeSDKClient(options)
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
