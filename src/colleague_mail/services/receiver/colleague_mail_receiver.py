from logging import getLogger

from src.colleague_mail.models.assistant_key import ASSISTANT_ACCOUNT_PREFIX
from src.colleague_mail.services.entities.incoming_mail import IncomingMail
from src.colleague_mail.services.entities.receive_outcome import ReceiveOutcome
from src.colleague_mail.services.receiver.protocols.i_incoming_mail_journal import (
    IIncomingMailJournal,
)
from src.colleague_mail.services.receiver.protocols.i_mail_body_parser import (
    IMailBodyParser,
)

logger = getLogger(__name__)

NUL = "\x00"
REPLACEMENT_CHARACTER = "�"


class ColleagueMailReceiver:
    def __init__(
        self, journal: IIncomingMailJournal, parser: IMailBodyParser, own_key: str
    ) -> None:
        self._journal = journal
        self._parser = parser
        self._own_key = own_key

    def receive(self, incoming: IncomingMail) -> ReceiveOutcome:
        if not incoming.message_id or not incoming.user_id:
            logger.warning(
                "Colleague mail rejected: user_id=%r message_id=%r",
                incoming.user_id,
                incoming.message_id,
            )
            return ReceiveOutcome.REJECTED
        if not incoming.user_id.startswith(ASSISTANT_ACCOUNT_PREFIX):
            logger.warning(
                "Colleague mail %s rejected: account %r is not an assistant",
                incoming.message_id,
                incoming.user_id,
            )
            return ReceiveOutcome.REJECTED

        body = self._parser.parse(incoming.body)
        if body is None:
            logger.warning("Colleague mail %s rejected: body", incoming.message_id)
            return ReceiveOutcome.REJECTED

        account_key = incoming.user_id.removeprefix(ASSISTANT_ACCOUNT_PREFIX)
        if body.sender != account_key:
            logger.warning(
                "Colleague mail %s rejected: from=%r but sent by account %r",
                incoming.message_id,
                body.sender,
                incoming.user_id,
            )
            return ReceiveOutcome.REJECTED
        if body.recipient != self._own_key:
            logger.warning(
                "Colleague mail %s rejected: addressed to %r, this assistant is %r",
                incoming.message_id,
                body.recipient,
                self._own_key,
            )
            return ReceiveOutcome.REJECTED

        recorded = self._journal.record_incoming(
            message_id=incoming.message_id,
            sender=body.sender,
            message_type=body.type,
            text=_storable(body.text),
            about_agent=_storable(body.about_agent) if body.about_agent else None,
            in_reply_to=_storable(body.in_reply_to) if body.in_reply_to else None,
            sent_at=incoming.published_at,
        )
        if not recorded:
            logger.info("Colleague mail %s already recorded", incoming.message_id)
            return ReceiveOutcome.DUPLICATE
        logger.info(
            "Colleague mail %s (%s) from %s recorded",
            incoming.message_id,
            body.type,
            body.sender,
        )
        return ReceiveOutcome.RECORDED


def _storable(text: str) -> str:
    return text.replace(NUL, REPLACEMENT_CHARACTER)
