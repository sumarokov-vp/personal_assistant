from datetime import datetime

from pydantic import BaseModel

from src.agent_notifications.services.entities.incoming_attachment import (
    IncomingAttachment,
)


class IncomingNotification(BaseModel):
    message_id: str | None
    sender: str | None
    body: str
    published_at: datetime | None
    attachment: IncomingAttachment | None = None
