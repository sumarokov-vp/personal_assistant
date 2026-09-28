from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LinkState(BaseModel):
    model_config = ConfigDict(frozen=True)

    linked: bool
    checked_at: datetime
