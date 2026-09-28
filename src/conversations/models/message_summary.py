from pydantic import BaseModel, ConfigDict


class MessageSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    message_id: str
    conversation_id: str
    title: str
    sender: str
    date: str
    snippet: str
    has_attachments: bool
    link: str | None = None
