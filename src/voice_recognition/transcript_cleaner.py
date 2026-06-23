import asyncio
from pathlib import Path

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query

CLEANUP_PROMPT = (
    "Вот сырая транскрипция устной речи, полученная распознавателем Whisper.\n"
    "Причеши её: восстанови пунктуацию и разбивку на абзацы, убери слова-паразиты, "
    "оговорки и повторы, исправь очевидные ошибки распознавания. "
    "НЕ меняй смысл, НЕ сокращай содержание, НЕ добавляй ничего от себя, не комментируй. "
    "Верни только причёсанный текст, без вступлений и пояснений.\n\n"
    "Транскрипция:\n"
)


class TranscriptCleaner:
    def clean(self, raw_text: str) -> str:
        return asyncio.run(self._clean_async(raw_text))

    async def _clean_async(self, raw_text: str) -> str:
        options = ClaudeAgentOptions(
            cwd=str(Path.home()),
            system_prompt={"type": "preset", "preset": "claude_code"},
            setting_sources=[],
            model="claude-haiku-4-5-20251001",
        )

        parts: list[str] = []
        result_text: str | None = None

        async for message in query(prompt=CLEANUP_PROMPT + raw_text, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        parts.append(block.text)
            elif isinstance(message, ResultMessage):
                result_text = message.result

        if parts:
            return "\n".join(parts).strip()
        return (result_text or "").strip()
