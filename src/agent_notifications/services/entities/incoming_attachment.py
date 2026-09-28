from pydantic import BaseModel


class IncomingAttachment(BaseModel):
    filename: str | None
    content: bytes
    path: str | None
    declared_size: int | None
