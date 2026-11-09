from pydantic import BaseModel, ConfigDict

from src.protocols.models.protocol_kind import ProtocolKind


class ProtocolRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    chat_id: int
    transcript_id: str
    kind: ProtocolKind
    archive_path: str | None = None
