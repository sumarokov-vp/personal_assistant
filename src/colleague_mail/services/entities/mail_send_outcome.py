from enum import StrEnum


class MailSendOutcome(StrEnum):
    IN_RECIPIENT_INBOX = "in_recipient_inbox"
    NO_RECIPIENT = "no_recipient"
    BROKER_UNAVAILABLE = "broker_unavailable"
