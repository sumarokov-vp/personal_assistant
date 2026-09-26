from ai_framework import Message
from ai_framework.protocols.i_ai_provider import IAIProvider

CLEANUP_PROMPT = (
    "Вот сырая транскрипция устной речи, полученная распознавателем Whisper.\n"
    "Причеши её: восстанови пунктуацию и разбивку на абзацы, убери слова-паразиты, "
    "оговорки и повторы, исправь очевидные ошибки распознавания. "
    "НЕ меняй смысл, НЕ сокращай содержание, НЕ добавляй ничего от себя, не комментируй. "
    "Верни только причёсанный текст, без вступлений и пояснений.\n\n"
    "Транскрипция:\n"
)


class TranscriptCleaner:
    def __init__(self, ai_provider: IAIProvider) -> None:
        self._ai_provider = ai_provider

    def clean(self, raw_text: str) -> str:
        response = self._ai_provider.send_message(
            [Message(role="user", content=CLEANUP_PROMPT + raw_text)],
        )
        return (response.content or "").strip()
