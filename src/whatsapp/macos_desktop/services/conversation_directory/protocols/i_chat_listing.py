from typing import Protocol

from src.whatsapp.macos_desktop.models.whatsapp_chat_row import WhatsAppChatRow


class IChatListing(Protocol):
    def list_chats(
        self, title_contains: str | None, limit: int
    ) -> list[WhatsAppChatRow]: ...
