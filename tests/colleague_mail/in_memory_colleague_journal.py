from dataclasses import dataclass, field
from datetime import datetime

from src.colleague_mail.models import ColleagueMessageType, MessageDirection


@dataclass(frozen=True)
class JournalEntry:
    message_id: str
    direction: MessageDirection
    peer: str
    message_type: ColleagueMessageType
    text: str
    about_agent: str | None
    in_reply_to: str | None
    sent_at: datetime | None


@dataclass
class InMemoryColleagueJournal:
    entries: list[JournalEntry] = field(default_factory=list)

    def record_incoming(
        self,
        message_id: str,
        sender: str,
        message_type: ColleagueMessageType,
        text: str,
        about_agent: str | None,
        in_reply_to: str | None,
        sent_at: datetime | None,
    ) -> bool:
        if any(
            entry.message_id == message_id
            and entry.direction is MessageDirection.INCOMING
            for entry in self.entries
        ):
            return False
        self.entries.append(
            JournalEntry(
                message_id=message_id,
                direction=MessageDirection.INCOMING,
                peer=sender,
                message_type=message_type,
                text=text,
                about_agent=about_agent,
                in_reply_to=in_reply_to,
                sent_at=sent_at,
            )
        )
        return True

    def record_outgoing(
        self,
        message_id: str,
        recipient: str,
        message_type: ColleagueMessageType,
        text: str,
        about_agent: str | None,
        in_reply_to: str | None,
        sent_at: datetime,
    ) -> None:
        self.entries.append(
            JournalEntry(
                message_id=message_id,
                direction=MessageDirection.OUTGOING,
                peer=recipient,
                message_type=message_type,
                text=text,
                about_agent=about_agent,
                in_reply_to=in_reply_to,
                sent_at=sent_at,
            )
        )
