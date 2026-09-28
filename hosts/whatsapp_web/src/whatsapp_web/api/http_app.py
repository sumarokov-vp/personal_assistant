from collections.abc import Sequence

from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import BaseRoute, Route
from starlette.types import Lifespan

from whatsapp_web.api.bearer_key_guard import BearerKeyGuard
from whatsapp_web.api.documents_fetch_endpoint import DocumentsFetchEndpoint
from whatsapp_web.api.error_responder import ErrorResponder
from whatsapp_web.api.health_endpoint import HealthEndpoint
from whatsapp_web.api.protocols.i_document_fetch import IDocumentFetch
from whatsapp_web.api.protocols.i_link_status import ILinkStatus
from whatsapp_web.documents.errors.document_fetch_error import DocumentFetchError


def build_http_app(
    fetcher: IDocumentFetch,
    link_status: ILinkStatus,
    api_key: str,
    lifespan: Lifespan[Starlette] | None = None,
    extra_routes: Sequence[BaseRoute] = (),
) -> Starlette:
    responder = ErrorResponder()
    routes: list[BaseRoute] = [
        Route(
            "/v1/documents/fetch",
            DocumentsFetchEndpoint(fetcher).handle,
            methods=["POST"],
        ),
        Route("/v1/health", HealthEndpoint(link_status).handle, methods=["GET"]),
        *extra_routes,
    ]
    return Starlette(
        routes=routes,
        middleware=[Middleware(BearerKeyGuard, api_key=api_key)],
        exception_handlers={
            DocumentFetchError: responder.fetch_failed,
            ValidationError: responder.bad_request,
            Exception: responder.internal,
        },
        lifespan=lifespan,
    )
