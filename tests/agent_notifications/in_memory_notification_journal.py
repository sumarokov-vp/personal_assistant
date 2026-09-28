from datetime import UTC, datetime

from src.agent_notifications.models.agent_notification import AgentNotification


class InMemoryNotificationJournal:
    def __init__(self) -> None:
        self.notifications: dict[str, AgentNotification] = {}

    def record(
        self,
        message_id: str,
        source: str,
        body: str,
        published_at: datetime | None,
        file_name: str | None = None,
        file_size: int | None = None,
    ) -> AgentNotification:
        if message_id not in self.notifications:
            self.notifications[message_id] = AgentNotification(
                id=len(self.notifications) + 1,
                message_id=message_id,
                source=source,
                body=body,
                published_at=published_at,
                received_at=datetime.now(UTC),
                delivered_at=None,
                file_name=file_name,
                file_size=file_size,
            )
        return self.notifications[message_id]

    def mark_delivered(self, message_id: str) -> None:
        self.notifications[message_id] = self.notifications[message_id].model_copy(
            update={"delivered_at": datetime.now(UTC)}
        )
