from datetime import datetime

from pydantic import BaseModel


class AgentNotification(BaseModel):
    id: int
    message_id: str
    source: str
    body: str
    published_at: datetime | None
    received_at: datetime
    delivered_at: datetime | None
