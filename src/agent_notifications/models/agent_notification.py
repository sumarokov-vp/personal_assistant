from datetime import datetime

from pydantic import BaseModel

from src.agent_notifications.models.human_size import human_size


class AgentNotification(BaseModel):
    id: int
    message_id: str
    source: str
    body: str
    published_at: datetime | None
    received_at: datetime
    delivered_at: datetime | None
    file_name: str | None = None
    file_size: int | None = None

    @property
    def file_label(self) -> str | None:
        if self.file_name is None:
            return None
        if self.file_size is None:
            return f"файл {self.file_name}"
        return f"файл {self.file_name} ({human_size(self.file_size)})"
