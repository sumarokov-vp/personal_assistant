import json
from datetime import datetime

import pytest

from src.colleague_mail.models import ColleagueMessageType, MessageDirection
from src.colleague_mail.services.entities import MailSendOutcome, OutgoingMail
from src.colleague_mail.services.sender import ColleagueMailSender
from tests.colleague_mail.in_memory_colleague_journal import InMemoryColleagueJournal


class RecordingPublisher:
    def __init__(self, outcome: MailSendOutcome) -> None:
        self.outcome = outcome
        self.published: list[dict[str, object]] = []

    def publish(
        self,
        message_id: str,
        recipient: str,
        message_type: ColleagueMessageType,
        body: bytes,
        published_at: datetime,
    ) -> MailSendOutcome:
        self.published.append(
            {
                "message_id": message_id,
                "recipient": recipient,
                "type": message_type,
                "body": json.loads(body),
            }
        )
        return self.outcome


OUTGOING = OutgoingMail(
    recipient="yura",
    type=ColleagueMessageType.REMARK,
    text="Агент бухгалтерии путает НДС",
    about_agent="accountant",
)


def send(
    outcome: MailSendOutcome,
) -> tuple[RecordingPublisher, InMemoryColleagueJournal, str]:
    publisher = RecordingPublisher(outcome)
    journal = InMemoryColleagueJournal()
    result = ColleagueMailSender(
        publisher=publisher, journal=journal, own_key="sumarokov"
    ).send(OUTGOING)
    assert result.outcome is outcome
    return publisher, journal, result.message_id


def test_publishes_format_v1_and_journals_delivered() -> None:
    publisher, journal, message_id = send(MailSendOutcome.IN_RECIPIENT_INBOX)

    assert publisher.published == [
        {
            "message_id": message_id,
            "recipient": "yura",
            "type": ColleagueMessageType.REMARK,
            "body": {
                "v": 1,
                "from": "sumarokov",
                "to": "yura",
                "type": "remark",
                "text": "Агент бухгалтерии путает НДС",
                "about_agent": "accountant",
            },
        }
    ]
    [entry] = journal.entries
    assert (entry.message_id, entry.direction, entry.peer) == (
        message_id,
        MessageDirection.OUTGOING,
        "yura",
    )


@pytest.mark.parametrize(
    "outcome", [MailSendOutcome.NO_RECIPIENT, MailSendOutcome.BROKER_UNAVAILABLE]
)
def test_undelivered_mail_is_not_journaled(outcome: MailSendOutcome) -> None:
    _, journal, _ = send(outcome)

    assert journal.entries == []
