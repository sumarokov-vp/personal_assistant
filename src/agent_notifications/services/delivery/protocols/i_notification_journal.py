from datetime import datetime
from typing import Protocol

from src.agent_notifications.models.agent_notification import AgentNotification


class INotificationJournal(Protocol):
    def record(
        self,
        message_id: str,
        source: str,
        body: str,
        published_at: datetime | None,
    ) -> AgentNotification: ...

    def mark_delivered(self, message_id: str) -> None: ...
