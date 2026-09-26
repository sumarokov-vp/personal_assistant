from pydantic import BaseModel

from src.gmail.models.mail_attachment import MailAttachment


class MailAttachmentSource(BaseModel):
    attachment: MailAttachment
    gmail_attachment_id: str | None
    inline_bytes: bytes | None
