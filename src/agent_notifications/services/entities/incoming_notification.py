from datetime import datetime

from pydantic import BaseModel


class IncomingNotification(BaseModel):
    message_id: str | None
    sender: str | None
    body: str
    published_at: datetime | None
