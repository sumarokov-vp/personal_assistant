from whatsapp_web.documents.errors.not_linked_error import NotLinkedError
from whatsapp_web.documents.models.document_request import DocumentRequest
from whatsapp_web.documents.models.fetched_document import FetchedDocument
from whatsapp_web.link.services.link_aware_fetcher.protocols.i_document_fetch import (
    IDocumentFetch,
)
from whatsapp_web.link.services.link_aware_fetcher.protocols.i_last_link_state import (
    ILastLinkState,
)
from whatsapp_web.link.services.link_aware_fetcher.protocols.i_relink import IRelink


class LinkAwareFetcher:
    def __init__(
        self, fetcher: IDocumentFetch, last_state: ILastLinkState, relink: IRelink
    ) -> None:
        self._fetcher = fetcher
        self._last_state = last_state
        self._relink = relink

    async def fetch(self, request: DocumentRequest) -> FetchedDocument:
        known = self._last_state.last()
        if known is not None and not known.linked:
            self._relink.request_attempt(force=False)
            raise NotLinkedError(self._relink.not_linked_detail())
        return await self._fetcher.fetch(request)
