from typing import Protocol

from src.conversations.models.conversation_attachment import ConversationAttachment
from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow


class IAttachmentDescriber(Protocol):
    def describe(self, row: WhatsAppMessageRow) -> ConversationAttachment | None: ...
