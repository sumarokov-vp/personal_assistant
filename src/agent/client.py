import asyncio
import threading
from logging import getLogger
from typing import Any

import telebot
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)

from src.agent.tools.registry import SessionRegistry

logger = getLogger(__name__)


class AgentClient:
    def __init__(
        self,
        session_registry: SessionRegistry,
        bot: telebot.TeleBot,
        mcp_server: Any | None = None,
    ) -> None:
        self._clients: dict[int, ClaudeSDKClient] = {}
        self._session_registry = session_registry
        self._bot = bot
        self._mcp_server = mcp_server
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    def _get_or_create_client(self, user_id: int) -> ClaudeSDKClient:
        if user_id not in self._clients:
            options = ClaudeAgentOptions(
                cwd="/home/sumarokov",
                permission_mode="bypassPermissions",
                system_prompt={"type": "preset", "preset": "claude_code"},
                tools={"type": "preset", "preset": "claude_code"},
                settings='{"enabledPlugins": {}}',
                setting_sources=["user", "project", "local"],
            )
            if self._mcp_server is not None:
                options.mcp_servers = {"bot-tools": self._mcp_server}
                options.allowed_tools = ["mcp__bot-tools__*"]
            self._clients[user_id] = ClaudeSDKClient(options)
        return self._clients[user_id]

    def send_message(self, user_id: int, chat_id: int, text: str) -> str:
        future = asyncio.run_coroutine_threadsafe(
            self._send_message_async(user_id, chat_id, text), self._loop
        )
        return future.result()

    async def _send_message_async(
        self, user_id: int, chat_id: int, text: str
    ) -> str:
        client = self._get_or_create_client(user_id)

        self._session_registry.set_context(user_id, chat_id, self._bot)

        if client._transport is None:
            await client.connect()

        await client.query(text)

        response_parts: list[str] = []
        result_text: str | None = None
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_parts.append(block.text)
                    elif isinstance(block, ThinkingBlock):
                        preview = block.thinking[:200]
                        logger.info("Thinking: %s", preview)
                    elif isinstance(block, ToolUseBlock):
                        logger.info("Tool call: %s", block.name)
                    elif isinstance(block, ToolResultBlock):
                        status = "error" if block.is_error else "ok"
                        logger.info("Tool result: %s", status)
            elif isinstance(message, ResultMessage):
                logger.info(
                    "Result: turns=%s, cost=$%.4f, duration=%dms",
                    message.num_turns,
                    message.total_cost_usd,
                    message.duration_ms,
                )
                if message.is_error:
                    await self._reset_client(user_id)
                    raise RuntimeError(f"Claude SDK error: {message.result}")
                result_text = message.result

        if response_parts:
            return "\n".join(response_parts)
        return result_text or ""

    async def _reset_client(self, user_id: int) -> None:
        if user_id in self._clients:
            await self._clients[user_id].disconnect()
            del self._clients[user_id]
