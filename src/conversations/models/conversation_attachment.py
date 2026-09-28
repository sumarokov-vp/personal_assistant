from pydantic import BaseModel, ConfigDict

from src.conversations.models.attachment_availability import AttachmentAvailability


class ConversationAttachment(BaseModel):
    model_config = ConfigDict(frozen=True)

    attachment_id: str
    name: str
    media_type: str
    size: int | None
    availability: AttachmentAvailability
    unavailable_reason: str | None = None
