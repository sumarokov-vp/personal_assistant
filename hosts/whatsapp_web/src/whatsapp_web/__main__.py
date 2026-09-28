import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from starlette.applications import Starlette

from whatsapp_web.api.http_app import build_http_app
from whatsapp_web.browser.models.browser_settings import BrowserSettings
from whatsapp_web.browser.repos.link_state_store import LinkStateStore
from whatsapp_web.browser.services.browser_session.browser_session import BrowserSession
from whatsapp_web.browser.services.link_probe.link_probe import LinkProbe
from whatsapp_web.browser.services.link_status.link_status import LinkStatus
from whatsapp_web.documents.services.document_fetcher.document_fetcher import (
    DocumentFetcher,
)

LISTEN_HOST = "127.0.0.1"
DEFAULT_PORT = "18790"
DEFAULT_PROFILE_DIR = "~/docker/personal_assistant/whatsapp-web/profile"
DEFAULT_IDLE_SECONDS = "600"
DEFAULT_REUPLOAD_SECONDS = "120"

logger = logging.getLogger("whatsapp_web")


def read_api_key() -> str:
    key_file = os.environ.get("WHATSAPP_WEB_KEY_FILE", "")
    if not key_file:
        raise SystemExit(
            "WHATSAPP_WEB_KEY_FILE is not set: path to the file whose first line is the API key"
        )
    lines = Path(key_file).expanduser().read_text().splitlines()
    key = lines[0].strip() if lines else ""
    if not key:
        raise SystemExit(f"{key_file}: first line (API key) is empty")
    return key


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


def build_app() -> Starlette:
    store = LinkStateStore()
    session = BrowserSession(read_browser_settings(), LinkProbe(), store)
    link_status = LinkStatus(store, session)
    fetcher = DocumentFetcher(
        session,
        float(
            os.environ.get("WHATSAPP_WEB_REUPLOAD_SECONDS", DEFAULT_REUPLOAD_SECONDS)
        ),
    )

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        idle_watch = asyncio.create_task(session.run_idle_watch())
        startup_check: asyncio.Task[object] = asyncio.create_task(link_status.refresh())
        startup_check.add_done_callback(log_startup_check)
        yield
        idle_watch.cancel()
        startup_check.cancel()
        await session.close()

    return build_http_app(fetcher, link_status, read_api_key(), lifespan=lifespan)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    port = int(os.environ.get("WHATSAPP_WEB_PORT", DEFAULT_PORT))
    uvicorn.run(build_app(), host=LISTEN_HOST, port=port, log_level="info")


if __name__ == "__main__":
    main()
