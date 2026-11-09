from pydantic import BaseModel

from src.protocols.services.protocol_maker.protocol_files import ProtocolFiles


class ProtocolRunResult(BaseModel):
    progress_message_id: int
    text_message_ids: list[int] = []
    pdf_message_id: int | None = None
    files: ProtocolFiles | None = None
    archive_error: str | None = None
    failure: str | None = None
