from pydantic import BaseModel, ConfigDict

from src.gmail.models.mail_attachment import MailAttachment


class MailAttachmentFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    attachment: MailAttachment
    content: bytes
