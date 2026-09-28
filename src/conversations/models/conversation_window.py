from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationWindow(BaseModel):
    model_config = ConfigDict(frozen=True)

    since: datetime | None = None
    until: datetime | None = None
    limit: int = Field(default=50, ge=1)
