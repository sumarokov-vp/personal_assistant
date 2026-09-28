from datetime import datetime

from pydantic import BaseModel


class IncomingMail(BaseModel):
    message_id: str | None
    user_id: str | None
    body: bytes
    published_at: datetime | None
