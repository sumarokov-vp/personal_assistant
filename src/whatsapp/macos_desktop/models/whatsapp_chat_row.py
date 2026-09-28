from pydantic import BaseModel, ConfigDict


class WhatsAppChatRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    chat_pk: int
    title: str | None
    jid: str | None
    session_type: int | None
    last_message_at: float | None
