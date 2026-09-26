from typing import Protocol

from src.agent_notifications.services.entities.delivery_outcome import DeliveryOutcome
from src.agent_notifications.services.entities.incoming_notification import (
    IncomingNotification,
)


class INotificationDelivery(Protocol):
    def deliver(self, incoming: IncomingNotification) -> DeliveryOutcome: ...
