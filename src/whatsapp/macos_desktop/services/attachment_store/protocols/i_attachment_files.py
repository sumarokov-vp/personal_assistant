from pathlib import Path
from typing import Protocol

from src.conversations.models.conversation_attachment import ConversationAttachment
from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow


class IAttachmentFiles(Protocol):
    def describe(self, row: WhatsAppMessageRow) -> ConversationAttachment | None: ...

    def local_file(self, row: WhatsAppMessageRow) -> Path | None: ...
