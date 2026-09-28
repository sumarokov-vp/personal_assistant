from typing import Protocol

from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow
from src.whatsapp.macos_desktop.services.remote_media.remote_media_state import (
    RemoteMediaState,
)


class IRemoteMediaState(Protocol):
    def state(self, row: WhatsAppMessageRow) -> RemoteMediaState: ...
