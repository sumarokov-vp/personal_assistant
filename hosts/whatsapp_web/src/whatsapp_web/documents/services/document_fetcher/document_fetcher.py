import mimetypes
import time

from whatsapp_web.documents.errors.chat_not_found_error import ChatNotFoundError
from whatsapp_web.documents.errors.document_not_found_error import DocumentNotFoundError
from whatsapp_web.documents.errors.not_linked_error import NotLinkedError
from whatsapp_web.documents.errors.reupload_timeout_error import ReuploadTimeoutError
from whatsapp_web.documents.errors.size_mismatch_error import SizeMismatchError
from whatsapp_web.documents.models.document_request import DocumentRequest
from whatsapp_web.documents.models.fetched_document import FetchedDocument
from whatsapp_web.documents.services.document_fetcher.downloaded_document import (
    DownloadedDocument,
)
from whatsapp_web.documents.services.document_fetcher.protocols.i_document_screen import (
    IDocumentScreen,
)
from whatsapp_web.documents.services.document_fetcher.protocols.i_screen_lease import (
    IScreenLease,
)

FALLBACK_CONTENT_TYPE = "application/octet-stream"


class DocumentFetcher:
    def __init__(self, screens: IScreenLease, reupload_timeout_seconds: float) -> None:
        self._screens = screens
        self._reupload_timeout_seconds = reupload_timeout_seconds

    async def fetch(self, request: DocumentRequest) -> FetchedDocument:
        started = time.monotonic()
        async with self._screens.lease() as screen:
            document = await self._fetch_on(screen, request)
        return FetchedDocument(
            file_name=document.shown_name,
            content=document.content,
            content_type=mimetypes.guess_type(document.shown_name)[0]
            or FALLBACK_CONTENT_TYPE,
            elapsed_ms=round((time.monotonic() - started) * 1000),
        )

    async def _fetch_on(
        self, screen: IDocumentScreen, request: DocumentRequest
    ) -> DownloadedDocument:
        if not await screen.is_linked():
            raise NotLinkedError()
        if not await screen.open_chat(request.chat_title, request.phone_digits):
            raise ChatNotFoundError()
        await screen.open_documents()
        candidates = await screen.count_documents(request.file_name)
        if candidates == 0:
            raise DocumentNotFoundError()
        received_sizes: list[int] = []
        for index in range(candidates):
            if index > 0:
                await screen.open_documents()
                await screen.count_documents(request.file_name)
            document = await screen.download_document(
                request.file_name, index, self._reupload_timeout_seconds
            )
            if document is None:
                raise ReuploadTimeoutError(self._reupload_timeout_seconds)
            if len(document.content) == request.size:
                return document
            received_sizes.append(len(document.content))
        raise SizeMismatchError(request.size, received_sizes)
