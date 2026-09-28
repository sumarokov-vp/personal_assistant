import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route

from whatsapp_web.api.http_app import build_http_app
from whatsapp_web.api.link_endpoint import LinkEndpoint
from whatsapp_web.browser.models.browser_settings import BrowserSettings
from whatsapp_web.browser.repos.link_state_store import LinkStateStore
from whatsapp_web.browser.services.browser_session.browser_session import BrowserSession
from whatsapp_web.browser.services.link_probe.link_probe import LinkProbe
from whatsapp_web.browser.services.link_status.link_status import LinkStatus
from whatsapp_web.documents.services.document_fetcher.document_fetcher import (
    DocumentFetcher,
)
from whatsapp_web.link.models.relink_settings import ONE_DAY, RelinkSettings
from whatsapp_web.link.services.link_aware_fetcher.link_aware_fetcher import (
    LinkAwareFetcher,
)
from whatsapp_web.link.services.link_watch.link_watch import LinkWatch
from whatsapp_web.link.services.relink_coordinator.relink_coordinator import (
    RelinkCoordinator,
)
from whatsapp_web.link.services.system_clock.system_clock import SystemClock
from whatsapp_web.notify.services.amqp_notice_publisher.amqp_notice_publisher import (
    AmqpNoticePublisher,
)
from whatsapp_web.notify.services.background_owner_notifier.background_owner_notifier import (
    BackgroundOwnerNotifier,
)
from whatsapp_web.notify.services.log_notice_publisher.log_notice_publisher import (
    LogNoticePublisher,
)

LISTEN_HOST = "127.0.0.1"
DEFAULT_PORT = "18790"
DEFAULT_PROFILE_DIR = "~/docker/personal_assistant/whatsapp-web/profile"
DEFAULT_IDLE_SECONDS = "600"
DEFAULT_REUPLOAD_SECONDS = "120"
DEFAULT_LINK_CHECK_SECONDS = str(ONE_DAY)
NOTICE_DRAIN_SECONDS = 20.0

logger = logging.getLogger("whatsapp_web")


def read_secrets() -> tuple[str, dict[str, str]]:
    key_file = os.environ.get("WHATSAPP_WEB_KEY_FILE", "")
    if not key_file:
        raise SystemExit(
            "WHATSAPP_WEB_KEY_FILE is not set: path to the file whose first line is the API key"
        )
    lines = Path(key_file).expanduser().read_text().splitlines()
    key = lines[0].strip() if lines else ""
    if not key:
        raise SystemExit(f"{key_file}: first line (API key) is empty")
    fields: dict[str, str] = {}
    for line in lines[1:]:
        name, separator, value = line.partition("=")
        if separator and value.strip():
            fields[name.strip()] = value.strip()
    return key, fields


def read_browser_settings() -> BrowserSettings:
    profile_dir = Path(
        os.environ.get("WHATSAPP_WEB_PROFILE_DIR", DEFAULT_PROFILE_DIR)
    ).expanduser()
    profile_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    return BrowserSettings(
        profile_dir=profile_dir,
        headless=os.environ.get("WHATSAPP_WEB_HEADLESS", "1") != "0",
        idle_seconds=float(
            os.environ.get("WHATSAPP_WEB_IDLE_SECONDS", DEFAULT_IDLE_SECONDS)
        ),
    )


def log_startup_check(task: asyncio.Task[object]) -> None:
    if task.cancelled():
        return
    error = task.exception()
    if error is not None:
        logger.error("startup link check failed: %s", error)


async def run_link_checks(watch: LinkWatch, interval_seconds: float) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await watch.check()
        except Exception as error:
            logger.error("scheduled link check failed: %r", error)


def build_notifier(notify_amqp_url: str | None) -> BackgroundOwnerNotifier:
    if notify_amqp_url:
        logger.info("owner notices go to agent-notify")
        return BackgroundOwnerNotifier(AmqpNoticePublisher(notify_amqp_url))
    logger.warning(
        "no notify_amqp_url in the secrets file: owner notices go to this log"
    )
    return BackgroundOwnerNotifier(LogNoticePublisher())


def build_app() -> Starlette:
    api_key, secrets = read_secrets()
    store = LinkStateStore()
    session = BrowserSession(read_browser_settings(), LinkProbe(), store)
    link_status = LinkStatus(store, session)
    notifier = build_notifier(secrets.get("notify_amqp_url"))
    relink = RelinkCoordinator(
        RelinkSettings(phone=secrets.get("phone")), session, notifier, SystemClock()
    )
    store.add_listener(relink)
    fetcher = LinkAwareFetcher(
        DocumentFetcher(
            session,
            float(
                os.environ.get(
                    "WHATSAPP_WEB_REUPLOAD_SECONDS", DEFAULT_REUPLOAD_SECONDS
                )
            ),
        ),
        store,
        relink,
    )
    watch = LinkWatch(link_status, relink)
    check_interval = float(
        os.environ.get("WHATSAPP_WEB_LINK_CHECK_SECONDS", DEFAULT_LINK_CHECK_SECONDS)
    )

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        idle_watch = asyncio.create_task(session.run_idle_watch())
        link_checks = asyncio.create_task(run_link_checks(watch, check_interval))
        startup_check: asyncio.Task[object] = asyncio.create_task(link_status.refresh())
        startup_check.add_done_callback(log_startup_check)
        yield
        idle_watch.cancel()
        link_checks.cancel()
        startup_check.cancel()
        await relink.close()
        try:
            await asyncio.wait_for(notifier.drain(), NOTICE_DRAIN_SECONDS)
        except TimeoutError:
            logger.error("owner notices not published before shutdown")
        await session.close()

    return build_http_app(
        fetcher,
        link_status,
        api_key,
        lifespan=lifespan,
        extra_routes=[
            Route("/v1/link", LinkEndpoint(relink).handle, methods=["POST"]),
        ],
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    port = int(os.environ.get("WHATSAPP_WEB_PORT", DEFAULT_PORT))
    uvicorn.run(build_app(), host=LISTEN_HOST, port=port, log_level="info")


if __name__ == "__main__":
    main()
