from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TelegramChat(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    conversation_id: str
    title: str
    is_group: bool
    link_base: str | None
    entity: object
    last_message_at: datetime | None = None
