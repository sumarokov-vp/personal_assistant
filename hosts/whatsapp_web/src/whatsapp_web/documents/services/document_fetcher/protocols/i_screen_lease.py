from contextlib import AbstractAsyncContextManager
from typing import Protocol

from whatsapp_web.documents.services.document_fetcher.protocols.i_document_screen import (
    IDocumentScreen,
)


class IScreenLease(Protocol):
    def lease(self) -> AbstractAsyncContextManager[IDocumentScreen]: ...
