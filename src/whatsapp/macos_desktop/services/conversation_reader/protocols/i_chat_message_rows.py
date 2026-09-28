from typing import Protocol

from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow


class IChatMessageRows(Protocol):
    def by_pk(self, message_pk: int) -> WhatsAppMessageRow | None: ...

    def in_chat(
        self, chat_pk: int, since: float | None, until: float | None, limit: int
    ) -> list[WhatsAppMessageRow]: ...

    def has_before(self, chat_pk: int, sent_at: float, message_pk: int) -> bool: ...
