from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from src.ai_tools.agent_notifications.protocols.i_agent_notification_entry import (
    IAgentNotificationEntry,
)


class IAgentNotificationJournal(Protocol):
    def received_between(
        self,
        start: datetime,
        end: datetime,
        source: str | None,
        limit: int,
    ) -> Sequence[IAgentNotificationEntry]: ...
