from pydantic import BaseModel


class MailSummary(BaseModel):
    id: str
    thread_id: str
    sender: str
    subject: str
    date: str
    snippet: str
    has_attachments: bool = False
