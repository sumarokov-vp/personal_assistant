from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.colleague_mail.models.assistant_key import ASSISTANT_KEY_PATTERN
from src.colleague_mail.models.colleague_message_type import ColleagueMessageType


class MailBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True, frozen=True)

    v: Literal[1] = 1
    sender: str = Field(
        validation_alias="from",
        serialization_alias="from",
        pattern=ASSISTANT_KEY_PATTERN,
    )
    recipient: str = Field(
        validation_alias="to", serialization_alias="to", pattern=ASSISTANT_KEY_PATTERN
    )
    type: ColleagueMessageType
    text: str = Field(min_length=1)
    in_reply_to: str | None = None
    about_agent: str | None = None

    def to_json_bytes(self) -> bytes:
        return self.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")
