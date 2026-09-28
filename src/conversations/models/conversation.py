from pydantic import BaseModel, ConfigDict

from src.conversations.models.conversation_message import ConversationMessage


class Conversation(BaseModel):
    model_config = ConfigDict(frozen=True)

    conversation_id: str
    title: str
    is_group: bool
    messages: list[ConversationMessage]
    has_earlier: bool
