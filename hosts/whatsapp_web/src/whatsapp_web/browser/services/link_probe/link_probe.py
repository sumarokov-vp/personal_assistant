import asyncio
import time
from datetime import UTC, datetime

from playwright.async_api import Page

from whatsapp_web.browser.models.link_state import LinkState
from whatsapp_web.browser.services.entities.web_locators import (
    LINKED_MARK,
    LOGIN_BY_PHONE_TEXT,
    LOGIN_MARK,
)
from whatsapp_web.documents.errors.ui_changed_error import UiChangedError

POLL_SECONDS = 0.5


class LinkProbe:
    def __init__(self, timeout_seconds: float = 90) -> None:
        self._timeout_seconds = timeout_seconds

    async def probe(self, page: Page) -> LinkState:
        linked = page.locator(LINKED_MARK)
        login = page.locator(LOGIN_MARK).or_(page.get_by_text(LOGIN_BY_PHONE_TEXT))
        deadline = time.monotonic() + self._timeout_seconds
        while time.monotonic() < deadline:
            if await linked.count():
                return LinkState(linked=True, checked_at=datetime.now(UTC))
            if await login.count():
                return LinkState(linked=False, checked_at=datetime.now(UTC))
            await asyncio.sleep(POLL_SECONDS)
        raise UiChangedError("состояние привязки")
