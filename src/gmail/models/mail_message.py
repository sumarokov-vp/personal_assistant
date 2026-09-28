from datetime import datetime

from pydantic import BaseModel

from src.gmail.models.mail_attachment import MailAttachment


class MailMessage(BaseModel):
    id: str
    thread_id: str
    sender: str
    recipients: str
    subject: str
    date: str
    body: str
    attachments: list[MailAttachment]
    snippet: str = ""
    received_at: datetime | None = None
    sent_by_owner: bool = False
