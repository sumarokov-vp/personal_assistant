from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WebDocumentRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    chat_title: str | None
    chat_jid: str
    file_name: str
    size: int
    sent_at: datetime | None
