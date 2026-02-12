import asyncio
from logging import getLogger

import telebot
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)

from src.agent.protocols.i_sdk_client_pool import ISDKClientPool
from src.agent.session_stats import SessionStats
from src.agent.tools.registry import SessionRegistry

logger = getLogger(__name__)


class AgentClient:
    def __init__(
        self,
        pool: ISDKClientPool,
        session_registry: SessionRegistry,
        bot: telebot.TeleBot,
    ) -> None:
        self._pool = pool
        self._stats: dict[int, SessionStats] = {}
        self._session_registry = session_registry
        self._bot = bot

    def get_context(self, user_id: int) -> str:
        stats = self._stats.get(user_id)
        if not stats:
            return "Нет активной сессии"
        return stats.format()

    def reset_client(self, user_id: int) -> None:
        self._pool.remove(user_id)
        self._stats.pop(user_id, None)

    def send_message(self, user_id: int, chat_id: int, text: str) -> str:
        future = asyncio.run_coroutine_threadsafe(
            self._send_message_async(user_id, chat_id, text), self._pool.loop
        )
        return future.result()

    async def _send_message_async(
        self, user_id: int, chat_id: int, text: str
    ) -> str:
        client = self._pool.get_or_create(user_id)

        self._session_registry.set_context(user_id, chat_id, self._bot)

        if client._transport is None:
            logger.info("Connecting SDK client for user=%s...", user_id)
            try:
                await client.connect()
            except Exception:
                logger.exception("SDK connect failed for user=%s", user_id)
                await self._reset_client_async(user_id)
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
                    await self._reset_client_async(user_id)
                    raise RuntimeError(f"Claude SDK error: {message.result}")
                result_text = message.result

        if response_parts:
            return "\n".join(response_parts)
        return result_text or ""

    async def _reset_client_async(self, user_id: int) -> None:
        self._pool.remove(user_id)
        self._stats.pop(user_id, None)
