from src.conversations.models.source_freshness import SourceFreshness
from src.whatsapp.macos_desktop.services.freshness.protocols.i_capture_marker import (
    ICaptureMarker,
)
from src.whatsapp.macos_desktop.services.freshness.protocols.i_last_message_date import (
    ILastMessageDate,
)
from src.whatsapp.macos_desktop.services.freshness.protocols.i_seconds_converter import (
    ISecondsConverter,
)


class WhatsAppFreshness:
    def __init__(
        self,
        messages: ILastMessageDate,
        marker: ICaptureMarker,
        clock: ISecondsConverter,
    ) -> None:
        self._messages = messages
        self._marker = marker
        self._clock = clock

    def freshness(self) -> SourceFreshness:
        last_seconds = self._messages.last_message_seconds()
        return SourceFreshness(
            last_message_at=None
            if last_seconds is None
            else self._clock.to_datetime(last_seconds),
            captured_at=self._marker.captured_at(),
        )
