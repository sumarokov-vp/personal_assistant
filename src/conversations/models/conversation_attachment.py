from pydantic import BaseModel, ConfigDict


class ConversationAttachment(BaseModel):
    model_config = ConfigDict(frozen=True)

    attachment_id: str
    name: str
    media_type: str
    size: int | None
    downloaded: bool
