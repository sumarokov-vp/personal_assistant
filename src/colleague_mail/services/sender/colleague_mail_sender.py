from datetime import UTC, datetime
from logging import getLogger
from uuid import uuid4

from src.colleague_mail.services.entities.mail_body import MailBody
from src.colleague_mail.services.entities.mail_send_outcome import MailSendOutcome
from src.colleague_mail.services.entities.outgoing_mail import OutgoingMail
from src.colleague_mail.services.sender.protocols.i_mail_publisher import (
    IMailPublisher,
)
from src.colleague_mail.services.sender.protocols.i_outgoing_mail_journal import (
    IOutgoingMailJournal,
)
from src.colleague_mail.services.sender.send_result import SendResult

logger = getLogger(__name__)


class ColleagueMailSender:
    def __init__(
        self, publisher: IMailPublisher, journal: IOutgoingMailJournal, own_key: str
    ) -> None:
        self._publisher = publisher
        self._journal = journal
        self._own_key = own_key

    def send(self, mail: OutgoingMail) -> SendResult:
        message_id = str(uuid4())
        sent_at = datetime.now(UTC)
        body = MailBody(
            sender=self._own_key,
            recipient=mail.recipient,
            type=mail.type,
            text=mail.text,
            in_reply_to=mail.in_reply_to,
            about_agent=mail.about_agent,
        )
        outcome = self._publisher.publish(
            message_id=message_id,
            recipient=mail.recipient,
            message_type=mail.type,
            body=body.to_json_bytes(),
            published_at=sent_at,
        )
        if outcome is MailSendOutcome.IN_RECIPIENT_INBOX:
            self._journal.record_outgoing(
                message_id=message_id,
                recipient=mail.recipient,
                message_type=mail.type,
                text=mail.text,
                about_agent=mail.about_agent,
                in_reply_to=mail.in_reply_to,
                sent_at=sent_at,
            )
        logger.info(
            "Colleague mail %s (%s) to %s: %s",
            message_id,
            mail.type,
            mail.recipient,
            outcome,
        )
        return SendResult(message_id=message_id, outcome=outcome)
