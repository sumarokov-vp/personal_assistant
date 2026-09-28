from typing import Protocol

from whatsapp_web.documents.models.document_request import DocumentRequest
from whatsapp_web.documents.models.fetched_document import FetchedDocument


class IDocumentFetch(Protocol):
    async def fetch(self, request: DocumentRequest) -> FetchedDocument: ...
