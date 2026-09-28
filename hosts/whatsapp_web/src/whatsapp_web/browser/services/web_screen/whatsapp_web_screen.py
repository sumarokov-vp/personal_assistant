import asyncio
import re
import time
from pathlib import Path

from playwright.async_api import Download, Locator, Page

from whatsapp_web.browser.models.link_state import LinkState
from whatsapp_web.browser.services.entities.web_locators import (
    CHAT_HEADER,
    CHAT_TITLES,
    DOCUMENT_ITEMS,
    DOCUMENT_PREVIEW_PREFIX,
    DOCUMENTS_TAB_NAME,
    DOWNLOAD_BUTTON,
    INTRO_DIALOG_BUTTON,
    INTRO_DIALOG_CONTINUE,
    MEDIA_SECTION_TEXT,
    SEARCH_BOX,
)
from whatsapp_web.browser.services.web_screen.preview_title_match import (
    PreviewTitleMatch,
)
from whatsapp_web.browser.services.web_screen.protocols.i_link_probe import ILinkProbe
from whatsapp_web.browser.services.web_screen.protocols.i_link_state_recorder import (
    ILinkStateRecorder,
)
from whatsapp_web.documents.errors.ui_changed_error import UiChangedError
from whatsapp_web.documents.services.document_fetcher.downloaded_document import (
    DownloadedDocument,
)

POLL_SECONDS = 0.3
STEP_SECONDS = 15.0
CHAT_SEARCH_SECONDS = 8.0
PANEL_SETTLE_SECONDS = 2.5
SCROLL_SETTLE_SECONDS = 1.0
MAX_SCROLLS = 40
MIN_PHONE_DIGITS = 7
CLOSE_PRESSES = 3


class WhatsAppWebScreen:
    def __init__(
        self, page: Page, probe: ILinkProbe, recorder: ILinkStateRecorder
    ) -> None:
        self._page = page
        self._probe = probe
        self._recorder = recorder

    async def link_state(self) -> LinkState:
        state = await self._probe.probe(self._page)
        await self._recorder.record(state)
        return state

    async def is_linked(self) -> bool:
        return (await self.link_state()).linked

    async def open_chat(self, title: str | None, phone_digits: str | None) -> bool:
        await self._close_panels()
        await self._dismiss_intro_dialog()
        for query in (title, phone_digits):
            if not query:
                continue
            index = await self._search_chat(query, title, phone_digits)
            if index is not None:
                await self._page.locator(CHAT_TITLES).nth(index).click()
                await self._require(
                    self._page.locator(CHAT_HEADER), "шапка чата", STEP_SECONDS
                )
                return True
        return False

    async def open_documents(self) -> None:
        documents_tab = self._page.get_by_role("tab", name=DOCUMENTS_TAB_NAME)
        if not await documents_tab.count():
            await self._click(self._page.locator(CHAT_HEADER), "данные контакта")
            await self._click(
                self._page.get_by_text(MEDIA_SECTION_TEXT), "медиа, ссылки и документы"
            )
        await self._click(documents_tab, "вкладка «Документы»")
        await asyncio.sleep(PANEL_SETTLE_SECONDS)

    async def count_documents(self, file_name: str) -> int:
        items = self._page.locator(DOCUMENT_ITEMS)
        seen = -1
        for _ in range(MAX_SCROLLS):
            found = await self._matching_documents(file_name)
            if found:
                return len(found)
            total = await items.count()
            if total in (0, seen):
                return 0
            seen = total
            await items.last.scroll_into_view_if_needed()
            await asyncio.sleep(SCROLL_SETTLE_SECONDS)
        return len(await self._matching_documents(file_name))

    async def download_document(
        self, file_name: str, index: int, timeout_seconds: float
    ) -> DownloadedDocument | None:
        deadline = time.monotonic() + timeout_seconds
        matches = await self._matching_documents(file_name)
        if index >= len(matches):
            raise UiChangedError("просмотр документа")
        preview = self._page.locator(DOCUMENT_ITEMS).nth(matches[index])
        await self._click(preview, "просмотр документа")
        button = self._page.locator(DOWNLOAD_BUTTON).first
        if not await self._appears(button, deadline - time.monotonic()):
            await self._close_panels()
            return None
        download = await self._download_by(button, deadline - time.monotonic())
        if download is None:
            await self._close_panels()
            return None
        content = Path(await download.path()).read_bytes()
        shown_name = download.suggested_filename or file_name
        await download.delete()
        await self._page.keyboard.press("Escape")
        return DownloadedDocument(shown_name=shown_name, content=content)

    async def _matching_documents(self, file_name: str) -> list[int]:
        titles: list[str] = await self._page.locator(DOCUMENT_ITEMS).evaluate_all(
            "els => els.map(e => e.getAttribute('title') || '')"
        )
        return PreviewTitleMatch(DOCUMENT_PREVIEW_PREFIX).indexes(titles, file_name)

    async def _download_by(
        self, button: Locator, timeout_seconds: float
    ) -> Download | None:
        arrived: asyncio.Future[Download] = asyncio.get_running_loop().create_future()

        def catch(download: Download) -> None:
            if not arrived.done():
                arrived.set_result(download)

        self._page.on("download", catch)
        await button.click()
        done, _ = await asyncio.wait({arrived}, timeout=max(timeout_seconds, 1.0))
        self._page.remove_listener("download", catch)
        if not done:
            return None
        return arrived.result()

    async def _search_chat(
        self, query: str, title: str | None, phone_digits: str | None
    ) -> int | None:
        box = self._page.locator(SEARCH_BOX).first
        await self._require(box, "поиск чата", STEP_SECONDS)
        await box.click()
        await box.fill(query)
        deadline = time.monotonic() + CHAT_SEARCH_SECONDS
        while time.monotonic() < deadline:
            titles: list[str] = await self._page.locator(CHAT_TITLES).evaluate_all(
                "els => els.map(e => e.getAttribute('title') || '')"
            )
            index = self._matching_chat(titles, title, phone_digits)
            if index is not None:
                return index
            await asyncio.sleep(POLL_SECONDS)
        return None

    @staticmethod
    def _matching_chat(
        titles: list[str], title: str | None, phone_digits: str | None
    ) -> int | None:
        wanted_title = title.strip().casefold() if title else None
        for index, candidate in enumerate(titles):
            if wanted_title and candidate.strip().casefold() == wanted_title:
                return index
            digits = re.sub(r"\D", "", candidate)
            if (
                phone_digits
                and len(digits) >= MIN_PHONE_DIGITS
                and digits == phone_digits
            ):
                return index
        return None

    async def _dismiss_intro_dialog(self) -> None:
        button = self._page.locator(INTRO_DIALOG_BUTTON, has_text=INTRO_DIALOG_CONTINUE)
        if await button.count():
            await button.first.click()

    async def _close_panels(self) -> None:
        for _ in range(CLOSE_PRESSES):
            await self._page.keyboard.press("Escape")
            await asyncio.sleep(POLL_SECONDS)

    async def _click(self, locator: Locator, step: str) -> None:
        await self._require(locator, step, STEP_SECONDS)
        await locator.first.click()

    async def _require(
        self, locator: Locator, step: str, timeout_seconds: float
    ) -> None:
        if not await self._appears(locator, timeout_seconds):
            raise UiChangedError(step)

    @staticmethod
    async def _appears(locator: Locator, timeout_seconds: float) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while True:
            if await locator.count():
                return True
            if time.monotonic() >= deadline:
                return False
            await asyncio.sleep(POLL_SECONDS)
