import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest

from whatsapp_web.documents.errors.chat_not_found_error import ChatNotFoundError
from whatsapp_web.documents.errors.document_not_found_error import DocumentNotFoundError
from whatsapp_web.documents.errors.not_linked_error import NotLinkedError
from whatsapp_web.documents.errors.reupload_timeout_error import ReuploadTimeoutError
from whatsapp_web.documents.errors.size_mismatch_error import SizeMismatchError
from whatsapp_web.documents.errors.ui_changed_error import UiChangedError
from whatsapp_web.documents.models.document_request import DocumentRequest
from whatsapp_web.documents.models.fetched_document import FetchedDocument
from whatsapp_web.documents.services.document_fetcher.document_fetcher import (
    DocumentFetcher,
)
from whatsapp_web.documents.services.document_fetcher.downloaded_document import (
    DownloadedDocument,
)

PDF = b"%PDF-1.7 fake"
SHOWN_NAME = "Выдуманный счёт.pdf"


class FakeScreen:
    def __init__(
        self,
        linked: bool = True,
        known_chats: tuple[str, ...] = ("Выдуманный чат",),
        documents: tuple[bytes | None, ...] = (PDF,),
        broken_step: str | None = None,
    ) -> None:
        self.linked = linked
        self.known_chats = known_chats
        self.documents = documents
        self.broken_step = broken_step
        self.chat_queries: list[tuple[str | None, str | None]] = []
        self.downloaded: list[int] = []

    async def is_linked(self) -> bool:
        return self.linked

    async def open_chat(self, title: str | None, phone_digits: str | None) -> bool:
        self.chat_queries.append((title, phone_digits))
        return title in self.known_chats or phone_digits in self.known_chats

    async def open_documents(self) -> None:
        if self.broken_step:
            raise UiChangedError(self.broken_step)

    async def count_documents(self, file_name: str) -> int:
        return len(self.documents) if file_name == "Выдуманный счёт.pdf" else 0

    async def download_document(
        self, file_name: str, index: int, timeout_seconds: float
    ) -> DownloadedDocument | None:
        self.downloaded.append(index)
        content = self.documents[index]
        if content is None:
            return None
        return DownloadedDocument(shown_name=SHOWN_NAME, content=content)


class FakeLease:
    def __init__(self, screen: FakeScreen) -> None:
        self.screen = screen

    @asynccontextmanager
    async def lease(self) -> AsyncIterator[FakeScreen]:
        yield self.screen


def request(**overrides: object) -> DocumentRequest:
    fields: dict[str, object] = {
        "chat_title": "Выдуманный чат",
        "chat_jid": "70000000000@s.whatsapp.net",
        "file_name": "Выдуманный счёт.pdf",
        "size": len(PDF),
    }
    fields.update(overrides)
    return DocumentRequest.model_validate(fields)


def fetch_document(
    screen: FakeScreen, document_request: DocumentRequest
) -> FetchedDocument:
    fetcher = DocumentFetcher(FakeLease(screen), reupload_timeout_seconds=120)
    return asyncio.run(fetcher.fetch(document_request))


def fetch(screen: FakeScreen, document_request: DocumentRequest) -> bytes:
    return fetch_document(screen, document_request).content


def test_file_name_and_type_come_from_the_shown_document():
    document = fetch_document(FakeScreen(), request())
    assert document.file_name == SHOWN_NAME
    assert document.content_type == "application/pdf"


def test_returns_document_with_matching_size():
    assert fetch(FakeScreen(), request()) == PDF


def test_picks_candidate_by_size_among_same_names():
    screen = FakeScreen(documents=(b"%PDF other size", PDF))
    assert fetch(screen, request()) == PDF
    assert screen.downloaded == [0, 1]


def test_personal_chat_without_title_is_found_by_phone():
    screen = FakeScreen(known_chats=("70000000000",))
    assert fetch(screen, request(chat_title=None)) == PDF
    assert screen.chat_queries == [(None, "70000000000")]


def test_group_chat_has_no_phone():
    assert request(chat_jid="120363000000000000@g.us").phone_digits is None


def test_not_linked():
    with pytest.raises(NotLinkedError):
        fetch(FakeScreen(linked=False), request())


def test_chat_not_found():
    with pytest.raises(ChatNotFoundError):
        fetch(FakeScreen(known_chats=()), request())


def test_document_not_found():
    with pytest.raises(DocumentNotFoundError):
        fetch(FakeScreen(), request(file_name="Нет такого.pdf"))


def test_ui_changed_names_the_step():
    with pytest.raises(UiChangedError) as error:
        fetch(FakeScreen(broken_step="вкладка «Документы»"), request())
    assert "вкладка «Документы»" in error.value.detail


def test_reupload_timeout():
    with pytest.raises(ReuploadTimeoutError):
        fetch(FakeScreen(documents=(None,)), request())


def test_size_mismatch_lists_received_sizes():
    with pytest.raises(SizeMismatchError) as error:
        fetch(FakeScreen(documents=(b"12345",)), request())
    assert error.value.received == [5]
