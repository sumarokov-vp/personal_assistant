from typing import Protocol

from telethon.tl.custom.message import Message

from src.conversations.models.conversation_attachment import ConversationAttachment


class IAttachmentDescriber(Protocol):
    def attachments(self, message: Message) -> list[ConversationAttachment]: ...
