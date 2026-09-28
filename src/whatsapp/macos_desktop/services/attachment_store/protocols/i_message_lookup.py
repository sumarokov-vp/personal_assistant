from typing import Protocol

from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow


class IMessageLookup(Protocol):
    def by_pk(self, message_pk: int) -> WhatsAppMessageRow | None: ...
