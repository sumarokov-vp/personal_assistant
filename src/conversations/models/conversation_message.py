from pydantic import BaseModel, ConfigDict

from src.conversations.models.conversation_attachment import ConversationAttachment


class ConversationMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    message_id: str
    conversation_id: str
    title: str
    sender: str
    recipients: str
    from_owner: bool
    date: str
    text: str
    attachments: list[ConversationAttachment]
