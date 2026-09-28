from pydantic import BaseModel, ConfigDict


class ConversationSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    conversation_id: str
    title: str
    is_group: bool
    last_message_date: str
