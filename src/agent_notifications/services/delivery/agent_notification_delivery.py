from logging import getLogger

from bot_framework import ParseMode

from src.agent_notifications.models.agent_notification import AgentNotification
from src.agent_notifications.services.delivery.protocols.i_notification_journal import (
    INotificationJournal,
)
from src.agent_notifications.services.delivery.protocols.i_owner_message_sender import (
    IOwnerMessageSender,
)
from src.agent_notifications.services.delivery.protocols.i_text_splitter import (
    ITextSplitter,
)
from src.agent_notifications.services.entities.delivery_outcome import DeliveryOutcome
from src.agent_notifications.services.entities.incoming_notification import (
    IncomingNotification,
)

logger = getLogger(__name__)

SENDER_ACCOUNT_PREFIX = "agent-"
NUL = "\x00"
REPLACEMENT_CHARACTER = "�"


class AgentNotificationDelivery:
    def __init__(
        self,
        journal: INotificationJournal,
        message_sender: IOwnerMessageSender,
        splitter: ITextSplitter,
        owner_chat_id: int,
    ) -> None:
        self._journal = journal
        self._message_sender = message_sender
        self._splitter = splitter
        self._owner_chat_id = owner_chat_id

    def deliver(self, incoming: IncomingNotification) -> DeliveryOutcome:
        if not incoming.sender or not incoming.message_id:
            logger.warning(
                "Agent notification rejected: user_id=%r message_id=%r",
                incoming.sender,
                incoming.message_id,
            )
            return DeliveryOutcome.REJECTED

        stored = self._journal.record(
            message_id=incoming.message_id,
            source=incoming.sender.removeprefix(SENDER_ACCOUNT_PREFIX),
            body=incoming.body.replace(NUL, REPLACEMENT_CHARACTER),
            published_at=incoming.published_at,
        )
        if stored.delivered_at is not None:
            logger.info(
                "Agent notification %s already delivered, skipped", stored.message_id
            )
            return DeliveryOutcome.ALREADY_DELIVERED

        for chunk in self._splitter.split(_owner_text(stored)):
            self._message_sender.send(
                chat_id=self._owner_chat_id, text=chunk, parse_mode=ParseMode.PLAIN
            )
        self._journal.mark_delivered(stored.message_id)
        logger.info(
            "Agent notification %s from %s delivered", stored.message_id, stored.source
        )
        return DeliveryOutcome.DELIVERED


def _owner_text(notification: AgentNotification) -> str:
    return f"Агент {notification.source}:\n{notification.body}"
