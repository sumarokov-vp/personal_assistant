from pydantic import BaseModel, ConfigDict


class AttachmentContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: bytes
    name: str
    media_type: str
