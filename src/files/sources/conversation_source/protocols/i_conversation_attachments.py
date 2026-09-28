from typing import Protocol

from src.conversations.models.attachment_content import AttachmentContent
from src.conversations.models.conversation_attachment import ConversationAttachment


class IConversationAttachments(Protocol):
    def list_attachments(self, message_id: str) -> list[ConversationAttachment]: ...

    def fetch_attachment(
        self, message_id: str, attachment_id: str
    ) -> AttachmentContent: ...
