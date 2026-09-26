from pydantic import BaseModel


class MailDraft(BaseModel):
    id: str
    message_id: str
    thread_id: str
    recipient: str
    subject: str
    url: str
    attached: list[str] = []
    left_out: list[str] = []
