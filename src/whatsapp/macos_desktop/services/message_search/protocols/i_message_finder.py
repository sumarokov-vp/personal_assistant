from typing import Protocol

from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow


class IMessageFinder(Protocol):
    def search(
        self,
        text: str,
        chat_pk: int | None,
        participant: str | None,
        since: float | None,
        until: float | None,
        limit: int,
    ) -> list[WhatsAppMessageRow]: ...
