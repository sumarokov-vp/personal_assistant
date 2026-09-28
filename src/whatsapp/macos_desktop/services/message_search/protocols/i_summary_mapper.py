from typing import Protocol

from src.conversations.models.message_summary import MessageSummary
from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow


class ISummaryMapper(Protocol):
    def to_summary(self, row: WhatsAppMessageRow) -> MessageSummary: ...
