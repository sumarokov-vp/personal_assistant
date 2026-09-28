from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.colleague_mail.models import (
    ColleagueMessage,
    ColleagueMessageType,
    MessageDirection,
)

RECEIVED_AT = datetime(2026, 9, 28, 3, 0, tzinfo=UTC)


def incoming(
    message_id: int,
    peer: str,
    message_type: ColleagueMessageType,
    text: str,
    about_agent: str | None = None,
) -> ColleagueMessage:
    return ColleagueMessage(
        id=message_id,
        message_id=f"m-{message_id}",
        direction=MessageDirection.INCOMING,
        peer=peer,
        type=message_type,
        text=text,
        about_agent=about_agent,
        in_reply_to=None,
        sent_at=RECEIVED_AT,
        received_at=RECEIVED_AT,
        shown_at=None,
    )


@dataclass
class InMemoryUnshownJournal:
    messages: list[ColleagueMessage] = field(default_factory=list)

    def unshown_incoming(
        self, peer: str | None, message_type: str | None, limit: int | None
    ) -> list[ColleagueMessage]:
        unshown = [message for message in self.messages if message.shown_at is None]
        return unshown if limit is None else unshown[:limit]

    def mark_shown(self, ids: list[int]) -> None:
        now = datetime.now(tz=UTC)
        self.messages = [
            message.model_copy(update={"shown_at": now})
            if message.id in ids
            else message
            for message in self.messages
        ]
