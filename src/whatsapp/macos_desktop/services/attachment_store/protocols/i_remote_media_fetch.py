from typing import Protocol

from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow


class IRemoteMediaFetch(Protocol):
    def fetch(self, row: WhatsAppMessageRow, name: str, desktop_hint: str) -> bytes: ...
