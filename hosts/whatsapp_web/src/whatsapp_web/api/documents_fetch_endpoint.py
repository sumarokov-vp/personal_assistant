import logging

from starlette.requests import Request
from starlette.responses import Response

from whatsapp_web.api.file_name_header import file_name_header
from whatsapp_web.api.privacy_label import privacy_label
from whatsapp_web.api.protocols.i_document_fetch import IDocumentFetch
from whatsapp_web.documents.models.document_request import DocumentRequest

logger = logging.getLogger(__name__)


class DocumentsFetchEndpoint:
    def __init__(self, fetcher: IDocumentFetch) -> None:
        self._fetcher = fetcher

    async def handle(self, request: Request) -> Response:
        document_request = DocumentRequest.model_validate_json(await request.body())
        document = await self._fetcher.fetch(document_request)
        logger.info(
            "document fetched: chat=%s file=%s size=%d ms=%d",
            privacy_label(document_request.chat_jid),
            privacy_label(document_request.file_name),
            len(document.content),
            document.elapsed_ms,
        )
        return Response(
            content=document.content,
            media_type=document.content_type,
            headers={
                "X-File-Name": file_name_header(document.file_name),
                "X-Elapsed-Ms": str(document.elapsed_ms),
            },
        )
