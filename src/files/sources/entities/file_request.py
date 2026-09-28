from pydantic import BaseModel, ConfigDict


class FileRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    thread_id: str
    message_id: str | None = None
    attachment_id: str | None = None
    path: str | None = None
    name: str | None = None
