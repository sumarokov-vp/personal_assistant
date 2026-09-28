from pydantic import BaseModel, ConfigDict

from src.whatsapp.web_media.models.web_document_status import WebDocumentStatus


class WebDocumentOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: WebDocumentStatus
    content: bytes = b""
    reason: str = ""
