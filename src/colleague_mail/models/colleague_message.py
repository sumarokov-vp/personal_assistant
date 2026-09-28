from datetime import datetime

from pydantic import BaseModel

from src.colleague_mail.models.colleague_message_type import ColleagueMessageType
from src.colleague_mail.models.message_direction import MessageDirection


class ColleagueMessage(BaseModel):
    id: int
    message_id: str
    direction: MessageDirection
    peer: str
    type: ColleagueMessageType
    text: str
    about_agent: str | None
    in_reply_to: str | None
    sent_at: datetime | None
    received_at: datetime | None
    shown_at: datetime | None
