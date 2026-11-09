import asyncio
from logging import getLogger

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

from src.flows.recordings.services.protocol_drafter import ProtocolModelError

DEFAULT_TIMEOUT_SECONDS = 15 * 60
MAX_TURNS = 1

logger = getLogger(__name__)


class ClaudeProtocolModel:
    def __init__(
        self, model: str, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    ) -> None:
        self._model = model
        self._timeout_seconds = timeout_seconds

    def ask(self, system: str, prompt: str) -> str:
        return asyncio.run(
            asyncio.wait_for(self._ask(system, prompt), self._timeout_seconds)
        )

    async def _ask(self, system: str, prompt: str) -> str:
        options = ClaudeAgentOptions(
            model=self._model,
            system_prompt=system,
            tools=[],
            setting_sources=[],
            max_turns=MAX_TURNS,
        )
        texts: list[str] = []
        result: ResultMessage | None = None
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                texts.extend(
                    block.text
                    for block in message.content
                    if isinstance(block, TextBlock)
                )
            elif isinstance(message, ResultMessage):
                result = message
        if result is None:
            raise ProtocolModelError("модель не вернула ответ")
        usage = result.usage or {}
        logger.info(
            "Protocol model: %s, input %d tokens (cache read %d, cache write %d), output %d, %d ms",
            result.subtype,
            usage.get("input_tokens", 0),
            usage.get("cache_read_input_tokens", 0),
            usage.get("cache_creation_input_tokens", 0),
            usage.get("output_tokens", 0),
            result.duration_ms,
        )
        if result.is_error:
            details = "; ".join(result.errors or []) or result.result or result.subtype
            raise ProtocolModelError(f"модель ответила ошибкой: {details}")
        return result.result or "\n".join(texts)
