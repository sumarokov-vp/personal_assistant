from datetime import datetime
from zoneinfo import ZoneInfo

from src.ai_tools.whatsapp_common.protocols.i_source_freshness import (
    ISourceFreshness,
)


class WhatsAppFreshnessNote:
    def __init__(self, source: ISourceFreshness, timezone: ZoneInfo) -> None:
        self._source = source
        self._timezone = timezone

    def note(self) -> str:
        freshness = self._source.freshness()
        last_message = (
            f"последнее сообщение от {self._display(freshness.last_message_at)}"
            if freshness.last_message_at is not None
            else "сообщений в снимке нет"
        )
        captured = (
            f"снимок снят {self._display(freshness.captured_at)}"
            if freshness.captured_at is not None
            else "время снимка неизвестно"
        )
        return f"Снимок WhatsApp: {last_message}, {captured} ({self._timezone.key})."

    def _display(self, moment: datetime) -> str:
        return moment.astimezone(self._timezone).strftime("%d.%m.%Y %H:%M")
