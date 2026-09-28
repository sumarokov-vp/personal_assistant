from typing import Protocol

from src.whatsapp.macos_desktop.models.whatsapp_chat_row import WhatsAppChatRow


class IChatLookup(Protocol):
    def by_pk(self, chat_pk: int) -> WhatsAppChatRow | None: ...
