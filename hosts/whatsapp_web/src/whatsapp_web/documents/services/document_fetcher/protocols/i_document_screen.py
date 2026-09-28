from typing import Protocol

from whatsapp_web.documents.services.document_fetcher.downloaded_document import (
    DownloadedDocument,
)


class IDocumentScreen(Protocol):
    async def is_linked(self) -> bool: ...

    async def open_chat(self, title: str | None, phone_digits: str | None) -> bool: ...

    async def open_documents(self) -> None: ...

    async def count_documents(self, file_name: str) -> int: ...

    async def download_document(
        self, file_name: str, index: int, timeout_seconds: float
    ) -> DownloadedDocument | None: ...
