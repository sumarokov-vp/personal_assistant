import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from starlette.routing import Route
from starlette.testclient import TestClient

from whatsapp_web.api.http_app import build_http_app
from whatsapp_web.api.link_endpoint import LinkEndpoint
from whatsapp_web.browser.models.link_state import LinkState
from whatsapp_web.browser.repos.link_state_store import LinkStateStore
from whatsapp_web.documents.errors.ui_changed_error import UiChangedError
from whatsapp_web.documents.models.document_request import DocumentRequest
from whatsapp_web.documents.models.fetched_document import FetchedDocument
from whatsapp_web.link.models.relink_settings import RelinkSettings
from whatsapp_web.link.models.relink_start import RelinkStart
from whatsapp_web.link.services.link_aware_fetcher.link_aware_fetcher import (
    LinkAwareFetcher,
)
from whatsapp_web.link.services.link_watch.link_watch import LinkWatch
from whatsapp_web.link.services.relink_coordinator.owner_messages import owner_time
from whatsapp_web.link.services.relink_coordinator.relink_coordinator import (
    RelinkCoordinator,
)

PHONE = "+70000000000"
START = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
API_KEY = "test-key"
AUTH = {"Authorization": f"Bearer {API_KEY}"}
BODY = {
    "chat_title": "Выдуманный чат",
    "chat_jid": "70000000000@s.whatsapp.net",
    "file_name": "Выдуманный счёт.pdf",
    "size": 13,
}


class FakeClock:
    def __init__(self) -> None:
        self.moment = START

    def now(self) -> datetime:
        return self.moment

    async def sleep(self, seconds: float) -> None:
        self.moment += timedelta(seconds=seconds)
        await asyncio.sleep(0)


class RecordingNotifier:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def notify(self, text: str) -> None:
        self.texts.append(text)

    def containing(self, fragment: str) -> list[str]:
        return [text for text in self.texts if fragment in text]


class FakeLinkPage:
    def __init__(
        self,
        store: LinkStateStore,
        clock: FakeClock,
        codes: tuple[str, ...] = ("AAAA1111",),
        linked_after_polls: int | None = None,
        broken_step: str | None = None,
    ) -> None:
        self.store = store
        self.clock = clock
        self.codes = codes
        self.linked_after_polls = linked_after_polls
        self.broken_step = broken_step
        self.linked = False
        self.polls = 0
        self.phones: list[str] = []
        self.hold = asyncio.Event()
        self.hold.set()

    async def link_state(self) -> LinkState:
        state = LinkState(linked=self.linked, checked_at=self.clock.now())
        await self.store.record(state)
        return state

    async def request_phone_code(self, phone: str) -> str:
        if self.broken_step:
            raise UiChangedError(self.broken_step)
        self.phones.append(phone)
        return self.codes[0]

    async def current_link_code(self) -> str | None:
        await self.hold.wait()
        self.polls += 1
        if (
            self.linked_after_polls is not None
            and self.polls >= self.linked_after_polls
        ):
            self.linked = True
        return self.codes[min(self.polls, len(self.codes) - 1)]


class FakePageLease:
    def __init__(self, page: FakeLinkPage) -> None:
        self.page = page
        self.leases = 0

    @asynccontextmanager
    async def lease(self) -> AsyncIterator[FakeLinkPage]:
        self.leases += 1
        yield self.page


class Rig:
    def __init__(
        self,
        phone: str | None = PHONE,
        codes: tuple[str, ...] = ("AAAA1111",),
        linked_after_polls: int | None = None,
        broken_step: str | None = None,
    ) -> None:
        self.clock = FakeClock()
        self.store = LinkStateStore()
        self.notifier = RecordingNotifier()
        self.page = FakeLinkPage(
            self.store, self.clock, codes, linked_after_polls, broken_step
        )
        self.lease = FakePageLease(self.page)
        self.coordinator = RelinkCoordinator(
            RelinkSettings(phone=phone), self.lease, self.notifier, self.clock
        )
        self.store.add_listener(self.coordinator)

    async def record(self, linked: bool) -> None:
        await self.store.record(LinkState(linked=linked, checked_at=self.clock.now()))


def test_startup_linked_sends_nothing():
    async def scenario() -> Rig:
        rig = Rig()
        await rig.record(linked=True)
        await rig.coordinator.wait_idle()
        return rig

    rig = asyncio.run(scenario())
    assert rig.notifier.texts == []
    assert rig.lease.leases == 0


def test_linked_to_unlinked_sends_exactly_one_unlinked_notice():
    async def scenario() -> Rig:
        rig = Rig()
        await rig.record(linked=True)
        await rig.record(linked=False)
        await rig.record(linked=False)
        await rig.coordinator.wait_idle()
        await rig.record(linked=False)
        await rig.coordinator.wait_idle()
        return rig

    rig = asyncio.run(scenario())
    assert len(rig.notifier.containing("отвязан")) == 1
    assert rig.notifier.texts[0].startswith("WhatsApp Web на Mac mini отвязан")
    assert rig.lease.leases == 1


def test_code_goes_to_owner_with_the_path_and_without_the_phone():
    async def scenario() -> Rig:
        rig = Rig(linked_after_polls=1)
        await rig.record(linked=True)
        await rig.record(linked=False)
        await rig.coordinator.wait_idle()
        return rig

    rig = asyncio.run(scenario())
    assert rig.page.phones == [PHONE]
    code_messages = rig.notifier.containing("AAAA-1111")
    assert len(code_messages) == 1
    assert "Связанные устройства → Привязать устройство" in code_messages[0]
    assert all(
        PHONE not in text and PHONE[1:] not in text for text in rig.notifier.texts
    )


def test_each_new_code_is_sent_but_not_more_than_three():
    codes = ("AAAA1111", "BBBB2222", "BBBB2222", "CCCC3333", "DDDD4444", "EEEE5555")

    async def scenario() -> Rig:
        rig = Rig(codes=codes)
        await rig.record(linked=False)
        await rig.coordinator.wait_idle()
        return rig

    rig = asyncio.run(scenario())
    sent = [text for text in rig.notifier.texts if "код привязки" in text.lower()]
    assert len(sent) == 3
    assert "AAAA-1111" in sent[0]
    assert "BBBB-2222" in sent[1] and "прежний больше не действует" in sent[1]
    assert "CCCC-3333" in sent[2]
    assert rig.notifier.containing("DDDD-4444") == []


def test_linking_by_code_reports_relinked():
    async def scenario() -> Rig:
        rig = Rig(linked_after_polls=2)
        await rig.record(linked=True)
        await rig.record(linked=False)
        await rig.coordinator.wait_idle()
        return rig

    rig = asyncio.run(scenario())
    assert rig.notifier.texts[-1].startswith("WhatsApp Web снова привязан")
    assert rig.notifier.containing("не привязался") == []
    last = rig.store.last()
    assert last is not None and last.linked


def test_window_without_linking_reports_and_holds_six_hour_cooldown():
    async def scenario() -> tuple[Rig, list[RelinkStart]]:
        rig = Rig()
        await rig.record(linked=False)
        await rig.coordinator.wait_idle()
        failed_at = rig.clock.now()
        starts: list[RelinkStart] = []
        rig.clock.moment = failed_at + timedelta(hours=5, minutes=59)
        starts.append(rig.coordinator.request_attempt(force=False))
        rig.clock.moment = failed_at + timedelta(hours=6, seconds=1)
        starts.append(rig.coordinator.request_attempt(force=False))
        await rig.coordinator.wait_idle()
        return rig, starts

    rig, starts = asyncio.run(scenario())
    assert starts == [RelinkStart.COOLDOWN, RelinkStart.STARTED]
    failures = rig.notifier.containing("не привязался за 15 мин")
    assert len(failures) == 2
    assert "POST /v1/link" in failures[0]
    assert rig.lease.leases == 2


def test_post_link_bypasses_cooldown():
    async def scenario() -> list[RelinkStart]:
        rig = Rig()
        await rig.record(linked=False)
        await rig.coordinator.wait_idle()
        rig.clock.moment += timedelta(hours=1)
        starts = [
            rig.coordinator.request_attempt(force=False),
            rig.coordinator.request_attempt(force=True),
            rig.coordinator.request_attempt(force=True),
        ]
        await rig.coordinator.wait_idle()
        return starts

    assert asyncio.run(scenario()) == [
        RelinkStart.COOLDOWN,
        RelinkStart.STARTED,
        RelinkStart.RUNNING,
    ]


def test_broken_layout_reports_the_step_and_cools_down():
    async def scenario() -> tuple[Rig, RelinkStart]:
        rig = Rig(broken_step="поле номера телефона")
        await rig.record(linked=False)
        await rig.coordinator.wait_idle()
        return rig, rig.coordinator.request_attempt(force=False)

    rig, start = asyncio.run(scenario())
    broken = rig.notifier.containing("сорвалась")
    assert len(broken) == 1
    assert "«поле номера телефона»" in broken[0]
    assert start is RelinkStart.COOLDOWN


def test_without_phone_only_the_notice_is_sent():
    async def scenario() -> Rig:
        rig = Rig(phone=None)
        await rig.record(linked=True)
        await rig.record(linked=False)
        await rig.coordinator.wait_idle()
        return rig

    rig = asyncio.run(scenario())
    assert len(rig.notifier.texts) == 1
    assert "Номера телефона нет" in rig.notifier.texts[0]
    assert rig.lease.leases == 0


def test_not_linked_detail_names_the_time_the_code_was_sent():
    async def scenario() -> tuple[str, str]:
        rig = Rig()
        rig.page.hold.clear()
        await rig.record(linked=False)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        detail = rig.coordinator.not_linked_detail()
        sent_at = owner_time(rig.clock.now())
        await rig.coordinator.close()
        return detail, sent_at

    detail, sent_at = asyncio.run(scenario())
    assert detail.startswith(
        f"WhatsApp Web не привязан: код отправлен в Telegram {sent_at}"
    )


def test_daily_check_starts_relinking_after_cooldown():
    class FakeLinkStatus:
        def __init__(self, rig: Rig) -> None:
            self.rig = rig
            self.refreshes = 0

        async def refresh(self) -> LinkState:
            self.refreshes += 1
            return await self.rig.page.link_state()

    async def scenario() -> tuple[Rig, FakeLinkStatus]:
        rig = Rig()
        status = FakeLinkStatus(rig)
        watch = LinkWatch(status, rig.coordinator)
        await watch.check()
        await rig.coordinator.wait_idle()
        rig.clock.moment += timedelta(hours=1)
        await watch.check()
        rig.clock.moment += timedelta(hours=6)
        await watch.check()
        await rig.coordinator.wait_idle()
        return rig, status

    rig, status = asyncio.run(scenario())
    assert status.refreshes == 3
    assert len(rig.notifier.containing("отвязан")) == 1
    assert rig.lease.leases == 2


class FakeFetcher:
    def __init__(self) -> None:
        self.requests: list[DocumentRequest] = []

    async def fetch(self, request: DocumentRequest) -> FetchedDocument:
        self.requests.append(request)
        return FetchedDocument(
            file_name=request.file_name,
            content=b"%PDF-1.7 fake",
            content_type="application/pdf",
            elapsed_ms=10,
        )


class FakeRelink:
    def __init__(self, start: RelinkStart = RelinkStart.STARTED) -> None:
        self.start = start
        self.requests: list[bool] = []

    def request_attempt(self, force: bool) -> RelinkStart:
        self.requests.append(force)
        return self.start

    def not_linked_detail(self) -> str:
        return "WhatsApp Web не привязан: код отправлен в Telegram 28.09.2026 15:00."


class FakeLinkStatus:
    async def current(self) -> LinkState:
        return LinkState(linked=False, checked_at=START)


def http_client(
    store: LinkStateStore, fetcher: FakeFetcher, relink: FakeRelink
) -> TestClient:
    app = build_http_app(
        LinkAwareFetcher(fetcher, store, relink),
        FakeLinkStatus(),
        API_KEY,
        extra_routes=[Route("/v1/link", LinkEndpoint(relink).handle, methods=["POST"])],
    )
    return TestClient(app, raise_server_exceptions=False)


def test_fetch_answers_409_not_linked_while_unlinked_without_touching_browser():
    store = LinkStateStore()
    asyncio.run(store.record(LinkState(linked=False, checked_at=START)))
    fetcher = FakeFetcher()
    relink = FakeRelink(RelinkStart.RUNNING)

    response = http_client(store, fetcher, relink).post(
        "/v1/documents/fetch", json=BODY, headers=AUTH
    )

    assert response.status_code == 409
    assert response.json() == {
        "error": "not_linked",
        "detail": "WhatsApp Web не привязан: код отправлен в Telegram 28.09.2026 15:00.",
    }
    assert fetcher.requests == []
    assert relink.requests == [False]


def test_fetch_goes_to_browser_while_linked():
    store = LinkStateStore()
    asyncio.run(store.record(LinkState(linked=True, checked_at=START)))
    fetcher = FakeFetcher()

    response = http_client(store, fetcher, FakeRelink()).post(
        "/v1/documents/fetch", json=BODY, headers=AUTH
    )

    assert response.status_code == 200
    assert len(fetcher.requests) == 1


def test_post_link_forces_an_attempt():
    relink = FakeRelink()
    client = http_client(LinkStateStore(), FakeFetcher(), relink)

    response = client.post("/v1/link", headers=AUTH)
    unauthorized = client.post("/v1/link")

    assert response.status_code == 202
    assert response.json()["relink"] == "started"
    assert relink.requests == [True]
    assert unauthorized.status_code == 401
