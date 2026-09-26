from pydantic import BaseModel


class MailAttachment(BaseModel):
    attachment_id: str
    filename: str
    media_type: str
    size: int
