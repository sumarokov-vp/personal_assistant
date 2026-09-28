from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

PERSONAL_CHAT_SUFFIX = "@s.whatsapp.net"


class DocumentRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    chat_jid: str = Field(min_length=1)
    file_name: str = Field(min_length=1)
    size: int = Field(gt=0)
    chat_title: str | None = None
    sent_at: datetime | None = None

    @property
    def phone_digits(self) -> str | None:
        if not self.chat_jid.endswith(PERSONAL_CHAT_SUFFIX):
            return None
        return self.chat_jid.removesuffix(PERSONAL_CHAT_SUFFIX).split(":")[0]
