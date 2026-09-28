from logging import getLogger

from bot_framework import ParseMode

from src.agent_notifications.models.agent_notification import AgentNotification
from src.agent_notifications.services.delivery.protocols.i_agent_file_store import (
    IAgentFileStore,
)
from src.agent_notifications.services.delivery.protocols.i_notification_journal import (
    INotificationJournal,
)
from src.agent_notifications.services.delivery.protocols.i_owner_document_sender import (
    IOwnerDocumentSender,
)
from src.agent_notifications.services.delivery.protocols.i_owner_message_sender import (
    IOwnerMessageSender,
)
from src.agent_notifications.services.delivery.protocols.i_text_splitter import (
    ITextSplitter,
)
from src.agent_notifications.services.entities.delivery_outcome import DeliveryOutcome
from src.agent_notifications.services.entities.incoming_attachment import (
    IncomingAttachment,
)
from src.agent_notifications.services.entities.incoming_notification import (
    IncomingNotification,
)

logger = getLogger(__name__)

SENDER_ACCOUNT_PREFIX = "agent-"
NUL = "\x00"
REPLACEMENT_CHARACTER = "�"
NO_DROPBOX_REFUSAL = "Dropbox боту не подключён (нет DROPBOX_ROOT)"


class AgentNotificationDelivery:
    def __init__(
        self,
        journal: INotificationJournal,
        message_sender: IOwnerMessageSender,
        document_sender: IOwnerDocumentSender,
        splitter: ITextSplitter,
        owner_chat_id: int,
        file_store: IAgentFileStore | None,
    ) -> None:
        self._journal = journal
        self._message_sender = message_sender
        self._document_sender = document_sender
        self._splitter = splitter
        self._owner_chat_id = owner_chat_id
        self._file_store = file_store

    def deliver(self, incoming: IncomingNotification) -> DeliveryOutcome:
        if not incoming.sender or not incoming.message_id:
            logger.warning(
                "Agent notification rejected: user_id=%r message_id=%r",
                incoming.sender,
                incoming.message_id,
            )
            return DeliveryOutcome.REJECTED
        source = incoming.sender.removeprefix(SENDER_ACCOUNT_PREFIX)
        if incoming.attachment is not None:
            return self._deliver_file(
                incoming.message_id, source, incoming, incoming.attachment
            )

        stored = self._journal.record(
            message_id=incoming.message_id,
            source=source,
            body=_clean(incoming.body),
            published_at=incoming.published_at,
        )
        if stored.delivered_at is not None:
            return self._already_delivered(stored)

        self._send_text(f"Агент {stored.source}:\n{stored.body}")
        return self._delivered(stored)

    def _deliver_file(
        self,
        message_id: str,
        source: str,
        incoming: IncomingNotification,
        attachment: IncomingAttachment,
    ) -> DeliveryOutcome:
        filename = _clean(attachment.filename or "").strip()
        if not filename:
            logger.warning("Agent file %s rejected: no filename", message_id)
            return DeliveryOutcome.REJECTED

        content: bytes | None = attachment.content
        store = self._file_store
        if attachment.path is not None:
            refusal = store.refusal(attachment.path) if store else NO_DROPBOX_REFUSAL
            if store is None or refusal is not None:
                logger.warning(
                    "Agent file %s rejected: path=%r — %s",
                    message_id,
                    attachment.path,
                    refusal,
                )
                return DeliveryOutcome.REJECTED
            content = store.read(attachment.path)

        stored = self._journal.record(
            message_id=message_id,
            source=source,
            body=_clean(incoming.body),
            published_at=incoming.published_at,
            file_name=filename,
            file_size=len(content) if content is not None else attachment.declared_size,
        )
        if stored.delivered_at is not None:
            return self._already_delivered(stored)

        if content is None:
            self._send_text(
                f"Агент {stored.source}: {stored.file_label} не дошёл — "
                "в Dropbox его уже нет"
            )
            return self._delivered(stored)

        self._send_text(_file_heading(stored))
        self._document_sender.send_document(
            chat_id=self._owner_chat_id, document=content, filename=filename
        )
        return self._delivered(stored)

    def _send_text(self, text: str) -> None:
        for chunk in self._splitter.split(text):
            self._message_sender.send(
                chat_id=self._owner_chat_id, text=chunk, parse_mode=ParseMode.PLAIN
            )

    def _already_delivered(self, stored: AgentNotification) -> DeliveryOutcome:
        logger.info(
            "Agent notification %s already delivered, skipped", stored.message_id
        )
        return DeliveryOutcome.ALREADY_DELIVERED

    def _delivered(self, stored: AgentNotification) -> DeliveryOutcome:
        self._journal.mark_delivered(stored.message_id)
        logger.info(
            "Agent notification %s from %s delivered", stored.message_id, stored.source
        )
        return DeliveryOutcome.DELIVERED


def _clean(text: str) -> str:
    return text.replace(NUL, REPLACEMENT_CHARACTER)


def _file_heading(notification: AgentNotification) -> str:
    heading = f"Агент {notification.source}: {notification.file_label}"
    if notification.body:
        return f"{heading}\n{notification.body}"
    return heading
