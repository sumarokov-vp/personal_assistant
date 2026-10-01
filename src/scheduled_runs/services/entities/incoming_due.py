from dataclasses import dataclass


@dataclass(frozen=True)
class IncomingDue:
    message_id: str | None
    sender: str | None
    message_type: str | None
    body: bytes
