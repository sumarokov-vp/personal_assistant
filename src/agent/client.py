import asyncio
import threading
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Any

import telebot
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)

from src.agent.tools.registry import SessionRegistry

logger = getLogger(__name__)


@dataclass
class SessionStats:
    model: str = ""
    session_id: str = ""
    total_cost_usd: float = 0.0
    total_turns: int = 0
    total_messages: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def update_from_result(self, result: ResultMessage) -> None:
        self.total_cost_usd += result.total_cost_usd or 0.0
        self.total_turns += result.num_turns
        self.total_messages += 1
        if result.usage:
            self.input_tokens += result.usage.get("input_tokens", 0)
            self.output_tokens += result.usage.get("output_tokens", 0)

    def update_from_init(self, data: dict[str, Any]) -> None:
        self.model = data.get("model", "")
        self.session_id = data.get("session_id", "")

    def format(self) -> str:
        lines = [
            f"Model: {self.model}",
            f"Messages: {self.total_messages}",
            f"Turns: {self.total_turns}",
            f"Tokens: {self.input_tokens} in / {self.output_tokens} out",
            f"Cost: ${self.total_cost_usd:.4f}",
        ]
        return "\n".join(lines)


class AgentClient:
    def __init__(
        self,
        session_registry: SessionRegistry,
        bot: telebot.TeleBot,
        mcp_server: Any | None = None,
    ) -> None:
        self._clients: dict[int, ClaudeSDKClient] = {}
        self._stats: dict[int, SessionStats] = {}
        self._session_registry = session_registry
        self._bot = bot
        self._mcp_server = mcp_server
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    def _get_or_create_client(self, user_id: int) -> ClaudeSDKClient:
        if user_id not in self._clients:
            options = ClaudeAgentOptions(
                cwd=str(Path.home()),
                permission_mode="bypassPermissions",
                system_prompt={"type": "preset", "preset": "claude_code"},
                tools={"type": "preset", "preset": "claude_code"},
                settings='{"enabledPlugins": {}}',
                # user/project/local нужны чтобы SDK подхватывал skills из ~/.claude/
                setting_sources=["user", "project", "local"],
                stderr=lambda line: logger.debug("CLI stderr: %s", line),
            )
            if self._mcp_server is not None:
                options.mcp_servers = {"bot-tools": self._mcp_server}
                options.allowed_tools = ["mcp__bot-tools__*"]
            self._clients[user_id] = ClaudeSDKClient(options)
        return self._clients[user_id]

    def get_context(self, user_id: int) -> str:
        stats = self._stats.get(user_id)
        if not stats:
            return "Нет активной сессии"
        return stats.format()

    def reset_client(self, user_id: int) -> None:
        future = asyncio.run_coroutine_threadsafe(
            self._reset_client(user_id), self._loop
        )
        future.result()

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
            logger.info("Connecting SDK client for user=%s...", user_id)
            try:
                await client.connect()
            except Exception:
                logger.exception("SDK connect failed for user=%s", user_id)
                await self._reset_client(user_id)
                raise
            logger.info("SDK client connected for user=%s", user_id)

        await client.query(text)

        stats = self._stats.setdefault(user_id, SessionStats())
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
            elif isinstance(message, SystemMessage):
                if message.subtype == "init":
                    stats.update_from_init(message.data)
            elif isinstance(message, ResultMessage):
                logger.info(
                    "Result: turns=%s, cost=$%.4f, duration=%dms",
                    message.num_turns,
                    message.total_cost_usd,
                    message.duration_ms,
                )
                stats.update_from_result(message)
                if message.is_error:
                    await self._reset_client(user_id)
                    raise RuntimeError(f"Claude SDK error: {message.result}")
                result_text = message.result

        if response_parts:
            return "\n".join(response_parts)
        return result_text or ""

    async def _reset_client(self, user_id: int) -> None:
        if user_id in self._clients:
            try:
                await self._clients[user_id].disconnect()
            except Exception:
                logger.debug("Disconnect error (cross-task cancel scope)", exc_info=True)
            del self._clients[user_id]
        self._stats.pop(user_id, None)
