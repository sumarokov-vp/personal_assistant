from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MessageQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str = ""
    conversation_id: str | None = None
    participant: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = Field(default=10, ge=1)
