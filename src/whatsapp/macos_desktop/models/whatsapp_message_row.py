from pydantic import BaseModel, ConfigDict


class WhatsAppMessageRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    message_pk: int
    chat_pk: int
    chat_title: str | None
    chat_jid: str | None
    session_type: int | None
    from_me: bool
    push_name: str | None
    member_name: str | None
    member_first_name: str | None
    sender_jid: str | None
    sent_at: float | None
    message_type: int | None
    body: str
    has_attachment: bool
    media_pk: int | None
    media_title: str | None
    media_size: int | None
    media_path: str | None
