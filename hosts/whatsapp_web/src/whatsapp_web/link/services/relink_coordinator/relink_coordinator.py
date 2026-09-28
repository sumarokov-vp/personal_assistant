import asyncio
import logging
from datetime import datetime, timedelta

from whatsapp_web.browser.models.link_state import LinkState
from whatsapp_web.documents.errors.document_fetch_error import DocumentFetchError
from whatsapp_web.documents.errors.ui_changed_error import UiChangedError
from whatsapp_web.link.models.relink_settings import RelinkSettings
from whatsapp_web.link.models.relink_start import RelinkStart
from whatsapp_web.link.services.relink_coordinator import owner_messages
from whatsapp_web.link.services.relink_coordinator.protocols.i_clock import IClock
from whatsapp_web.link.services.relink_coordinator.protocols.i_owner_notifier import (
    IOwnerNotifier,
)
from whatsapp_web.link.services.relink_coordinator.protocols.i_relink_screen import (
    IRelinkScreen,
)
from whatsapp_web.link.services.relink_coordinator.protocols.i_relink_screen_lease import (
    IRelinkScreenLease,
)

SECONDS_IN_MINUTE = 60

logger = logging.getLogger(__name__)


class RelinkCoordinator:
    def __init__(
        self,
        settings: RelinkSettings,
        screens: IRelinkScreenLease,
        notifier: IOwnerNotifier,
        clock: IClock,
    ) -> None:
        self._settings = settings
        self._screens = screens
        self._notifier = notifier
        self._clock = clock
        self._unlinked_noticed = False
        self._attempt: asyncio.Task[None] | None = None
        self._code_sent_at: datetime | None = None
        self._retry_after: datetime | None = None

    async def link_changed(self, state: LinkState) -> None:
        if state.linked:
            if self._unlinked_noticed:
                self._notifier.notify(owner_messages.RELINKED)
            self._unlinked_noticed = False
            self._code_sent_at = None
            self._retry_after = None
            return
        if not self._unlinked_noticed:
            self._unlinked_noticed = True
            self._notifier.notify(
                owner_messages.UNLINKED
                if self._settings.phone
                else owner_messages.UNLINKED_NO_PHONE
            )
        self.request_attempt(force=False)

    def attempt_running(self) -> bool:
        return self._attempt is not None and not self._attempt.done()

    def request_attempt(self, force: bool) -> RelinkStart:
        if self.attempt_running():
            return RelinkStart.RUNNING
        if not self._settings.phone:
            return RelinkStart.NO_PHONE
        if not force and self._in_cooldown():
            return RelinkStart.COOLDOWN
        self._attempt = asyncio.create_task(self._run_attempt(self._settings.phone))
        self._attempt.add_done_callback(self._attempt_finished)
        return RelinkStart.STARTED

    def not_linked_detail(self) -> str:
        if not self._settings.phone:
            return owner_messages.NOT_LINKED_NO_PHONE
        if self.attempt_running() and self._code_sent_at is not None:
            return owner_messages.not_linked_code_sent(self._code_sent_at)
        if self._retry_after is not None and self._in_cooldown():
            return owner_messages.not_linked_cooldown(self._retry_after)
        return owner_messages.NOT_LINKED_RUNNING

    async def wait_idle(self) -> None:
        if self._attempt is not None:
            await asyncio.wait({self._attempt})

    async def close(self) -> None:
        if self._attempt is not None:
            self._attempt.cancel()
            await asyncio.wait({self._attempt})

    async def _run_attempt(self, phone: str) -> None:
        self._code_sent_at = None
        async with self._screens.lease() as screen:
            if (await screen.link_state()).linked:
                return
            if await self._linked_by_code(screen, phone):
                return
        self._retry_after = self._clock.now() + self._cooldown()
        logger.info("relink window passed without linking")
        self._notifier.notify(
            owner_messages.not_linked_in_window(
                round(self._settings.window_seconds / SECONDS_IN_MINUTE),
                self._retry_after,
            )
        )

    async def _linked_by_code(self, screen: IRelinkScreen, phone: str) -> bool:
        code = await screen.request_phone_code(phone)
        self._send_code(owner_messages.first_code(code))
        codes_sent = 1
        deadline = self._clock.now() + timedelta(seconds=self._settings.window_seconds)
        while self._clock.now() < deadline:
            await self._clock.sleep(self._settings.poll_seconds)
            if (await screen.link_state()).linked:
                return True
            fresh = await screen.current_link_code()
            if fresh and fresh != code and codes_sent < self._settings.max_codes:
                code = fresh
                self._send_code(owner_messages.renewed_code(code))
                codes_sent += 1
        return False

    def _send_code(self, text: str) -> None:
        self._code_sent_at = self._clock.now()
        logger.info("link code sent to the owner")
        self._notifier.notify(text)

    def _attempt_finished(self, attempt: asyncio.Task[None]) -> None:
        if attempt.cancelled():
            return
        error = attempt.exception()
        if error is None:
            return
        self._retry_after = self._clock.now() + self._cooldown()
        logger.error("relink attempt failed: %r", error)
        self._notifier.notify(
            owner_messages.attempt_broken(self._reason(error), self._retry_after)
        )

    def _in_cooldown(self) -> bool:
        return self._retry_after is not None and self._clock.now() < self._retry_after

    def _cooldown(self) -> timedelta:
        return timedelta(seconds=self._settings.cooldown_seconds)

    @staticmethod
    def _reason(error: BaseException) -> str:
        if isinstance(error, UiChangedError):
            return f"на шаге «{error.step}» не нашёлся элемент — вёрстка WhatsApp Web изменилась."
        if isinstance(error, DocumentFetchError):
            return error.detail
        return (
            f"внутренняя ошибка {type(error).__name__}, подробности — в логе сервиса."
        )
