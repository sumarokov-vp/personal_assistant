from typing import Protocol

from src.whatsapp.web_media.models.web_document_outcome import WebDocumentOutcome
from src.whatsapp.web_media.models.web_document_request import WebDocumentRequest


class IDocumentFallback(Protocol):
    def fetch_document(self, request: WebDocumentRequest) -> WebDocumentOutcome: ...
