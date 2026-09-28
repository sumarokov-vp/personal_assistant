from pydantic import BaseModel, Field

from src.colleague_mail.models.assistant_key import ASSISTANT_KEY_PATTERN
from src.colleague_mail.models.colleague_message_type import ColleagueMessageType


class OutgoingMail(BaseModel):
    recipient: str = Field(pattern=ASSISTANT_KEY_PATTERN)
    type: ColleagueMessageType
    text: str = Field(min_length=1)
    in_reply_to: str | None = None
    about_agent: str | None = None
