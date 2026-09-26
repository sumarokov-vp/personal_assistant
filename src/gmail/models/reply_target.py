from pydantic import BaseModel


class ReplyTarget(BaseModel):
    thread_id: str
    recipient: str
    subject: str
    message_id_header: str
    references: str
