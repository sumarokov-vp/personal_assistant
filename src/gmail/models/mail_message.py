from pydantic import BaseModel


class MailMessage(BaseModel):
    id: str
    thread_id: str
    sender: str
    recipients: str
    subject: str
    date: str
    body: str
    attachment_names: list[str]
