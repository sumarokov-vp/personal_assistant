from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SourceFreshness(BaseModel):
    model_config = ConfigDict(frozen=True)

    last_message_at: datetime | None
    captured_at: datetime | None
