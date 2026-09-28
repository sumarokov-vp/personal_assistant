from typing import Protocol

from src.conversations.models.conversation_message import ConversationMessage
from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow


class IMessageMapper(Protocol):
    def to_message(self, row: WhatsAppMessageRow) -> ConversationMessage: ...
