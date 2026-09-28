import asyncio
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from whatsapp_web.browser.models.browser_settings import BrowserSettings
from whatsapp_web.browser.services.entities.web_locators import WEB_URL
from whatsapp_web.browser.services.web_screen.protocols.i_link_probe import ILinkProbe
from whatsapp_web.browser.services.web_screen.protocols.i_link_state_recorder import (
    ILinkStateRecorder,
)
from whatsapp_web.browser.services.web_screen.whatsapp_web_screen import (
    WhatsAppWebScreen,
)

IDLE_CHECK_SECONDS = 30.0
VIEWPORT_WIDTH = 1400
VIEWPORT_HEIGHT = 900

logger = logging.getLogger(__name__)


class BrowserSession:
    def __init__(
        self, settings: BrowserSettings, probe: ILinkProbe, recorder: ILinkStateRecorder
    ) -> None:
        self._settings = settings
        self._probe = probe
        self._recorder = recorder
        self._lock = asyncio.Lock()
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._last_used = time.monotonic()

    @asynccontextmanager
    async def lease(self) -> AsyncIterator[WhatsAppWebScreen]:
        async with self._lock:
            self._last_used = time.monotonic()
            page = await self._open_page()
            yield WhatsAppWebScreen(page, self._probe, self._recorder)
            self._last_used = time.monotonic()

    async def run_idle_watch(self) -> None:
        while True:
            await asyncio.sleep(IDLE_CHECK_SECONDS)
            await self.close_if_idle()

    async def close_if_idle(self) -> None:
        if self._context is None or self._lock.locked():
            return
        if time.monotonic() - self._last_used < self._settings.idle_seconds:
            return
        async with self._lock:
            await self._shutdown()
        logger.info("browser closed after %.0f s idle", self._settings.idle_seconds)

    async def close(self) -> None:
        async with self._lock:
            await self._shutdown()

    async def _open_page(self) -> Page:
        if self._page is not None and not self._page.is_closed():
            return self._page
        await self._shutdown()
        started = time.monotonic()
        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            str(self._settings.profile_dir),
            headless=self._settings.headless,
            user_agent=self._settings.user_agent,
            locale=self._settings.locale,
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            accept_downloads=True,
        )
        page = (
            self._context.pages[0]
            if self._context.pages
            else await self._context.new_page()
        )
        await page.goto(WEB_URL)
        self._page = page
        logger.info("browser launched in %.1f s", time.monotonic() - started)
        return page

    async def _shutdown(self) -> None:
        if self._context is not None:
            await self._context.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self._context = None
        self._playwright = None
        self._page = None
