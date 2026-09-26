from dataclasses import dataclass
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from ai_framework import BaseTool
from ai_framework.tools import ToolRegistry

from src.gmail.models.mail_message import MailMessage
from src.gmail.models.mail_summary import MailSummary
from src.memory.models import Deadline, Whereabouts
from src.memory.repos import DeadlineRepository, WhereaboutsRepository
from tests.memory.in_memory_wiki_storage import InMemoryWikiStorage
from workers.memory_fill.composition import (
    MEMORY_FILL_PROMPT_PATH,
    build_fill_system_prompt,
    build_kickoff,
    build_memory_fill_run,
    build_memory_fill_tools,
)
from workers.memory_fill.memory_fill_report import MemoryFillReport

TIMEZONE = ZoneInfo("Asia/Almaty")
PASSPORT_PATH = "03_home/01_personal_docs/Паспорт Владимир.txt"
TICKET_ID = "18c1a"

SCRIPT: list[tuple[str, dict[str, object]]] = [
    ("memory_show", {"page": "all"}),
    ("dropbox_search", {"query": "паспорт", "within": "03_home/01_personal_docs"}),
    ("dropbox_read", {"path": PASSPORT_PATH}),
    ("search_mail", {"query": "newer_than:1y ticket"}),
    ("read_mail", {"message_id": TICKET_ID}),
    (
        "memory_upsert_deadline",
        {
            "what": "Паспорт РФ",
            "whose": "Владимир",
            "expires": "2031-05-20",
            "source": PASSPORT_PATH,
        },
    ),
    (
        "memory_upsert_deadline",
        {
            "what": "Паспорт РФ",
            "whose": "Анна",
            "expires": "2029-08-01",
            "source": "03_home/01_personal_docs/Паспорт Анна.txt",
        },
    ),
    (
        "memory_upsert_trip",
        {
            "since": "2026-11-12",
            "place": "Чиангмай",
            "until": "2027-02-12",
            "purpose": "зимовка",
            "source": "почта: Your itinerary ALA-CNX",
        },
    ),
]


class FakeMailbox:
    def search_messages(self, query: str, limit: int) -> list[MailSummary]:
        return [
            MailSummary(
                id=TICKET_ID,
                thread_id="18c00",
                sender="AirAsia <no-reply@airasia.com>",
                subject="Your itinerary ALA-CNX",
                date="Sat, 26 Sep 2026 10:00:00 +0500",
                snippet="Almaty → Chiang Mai, 12 Nov 2026",
            )
        ]

    def get_message(self, message_id: str) -> MailMessage:
        return MailMessage(
            id=message_id,
            thread_id="18c00",
            sender="AirAsia <no-reply@airasia.com>",
            recipients="owner@example.com",
            subject="Your itinerary ALA-CNX",
            date="Sat, 26 Sep 2026 10:00:00 +0500",
            body="Almaty → Chiang Mai 12 Nov 2026, Chiang Mai → Almaty 12 Feb 2027",
            attachment_names=["itinerary.pdf"],
        )


@dataclass(frozen=True)
class ScriptedAnswer:
    content: str | None


class ScriptedConversation:
    def __init__(self, tools: list[BaseTool]) -> None:
        self._registry = ToolRegistry()
        for tool in tools:
            self._registry.register(tool)
        self.results: dict[str, str] = {}

    def process_message(self, thread_id: str, user_message: str) -> ScriptedAnswer:
        for number, (name, arguments) in enumerate(SCRIPT):
            result = self._registry.execute(name, arguments, f"call-{number}")
            assert not result.is_error, result.content
            self.results.setdefault(name, result.content)
        return ScriptedAnswer(content="Записал паспорта и зимовку в Чиангмае.")


@pytest.fixture
def dropbox_root(tmp_path: Path) -> Path:
    root = tmp_path / "Dropbox"
    documents = root / "03_home" / "01_personal_docs"
    documents.mkdir(parents=True)
    (documents / "Паспорт Владимир.txt").write_text(
        "Паспорт РФ, Владимир, действителен до 20.05.2031", encoding="utf-8"
    )
    (documents / "Паспорт Анна.txt").write_text(
        "Паспорт РФ, Анна, действителен до 01.08.2029", encoding="utf-8"
    )
    return root


def _wiki_with_old_passport() -> InMemoryWikiStorage:
    storage = InMemoryWikiStorage()
    DeadlineRepository(storage).upsert(
        Deadline(
            what="Паспорт РФ",
            whose="Владимир",
            expires=date(2021, 5, 20),
            renewal="МФЦ",
            source="вручную",
        )
    )
    return storage


def _run(
    dropbox_root: Path, storage: InMemoryWikiStorage
) -> tuple[MemoryFillReport, ScriptedConversation]:
    conversation = ScriptedConversation(
        build_memory_fill_tools(dropbox_root, FakeMailbox(), storage, TIMEZONE)
    )
    run = build_memory_fill_run(
        conversation,
        storage,
        build_kickoff(has_dropbox=True, has_mail=True),
        "memory_fill:test",
    )
    return run.execute(), conversation


def _counts(report: MemoryFillReport) -> dict[str, tuple[int, int]]:
    return {page.title: (page.added, page.updated) for page in report.pages}


def test_fill_writes_deadlines_and_trip_from_dropbox_and_mail(dropbox_root: Path):
    storage = _wiki_with_old_passport()

    report, conversation = _run(dropbox_root, storage)

    assert "20.05.2031" in conversation.results["dropbox_read"]
    assert "Chiang Mai" in conversation.results["read_mail"]
    assert _counts(report) == {
        "Реестр сроков": (1, 1),
        "Где я буду": (1, 0),
        "Обязательства": (0, 0),
    }
    deadlines = {
        (entry.what, entry.whose): entry
        for entry in DeadlineRepository(storage).read().entries
    }
    assert set(deadlines) == {("Паспорт РФ", "Владимир"), ("Паспорт РФ", "Анна")}
    assert deadlines["Паспорт РФ", "Владимир"].expires == date(2031, 5, 20)
    assert deadlines["Паспорт РФ", "Владимир"].renewal == "МФЦ"
    assert WhereaboutsRepository(storage).read().entries == [
        Whereabouts(
            since=date(2026, 11, 12),
            until=date(2027, 2, 12),
            place="Чиангмай",
            purpose="зимовка",
            source="почта: Your itinerary ALA-CNX",
        )
    ]
    assert "Реестр сроков: добавлено 1, обновлено 1" in report.render()


def test_second_fill_leaves_pages_unchanged(dropbox_root: Path):
    storage = _wiki_with_old_passport()
    _run(dropbox_root, storage)
    pages_after_first_run = dict(storage.files)

    report, _ = _run(dropbox_root, storage)

    assert storage.files == pages_after_first_run
    assert not report.has_changes


def test_fill_prompt_renders_without_unfilled_placeholders():
    prompt = build_fill_system_prompt(
        MEMORY_FILL_PROMPT_PATH.read_text(encoding="utf-8"), TIMEZONE
    )

    assert "{" not in prompt
    assert "03_home/01_personal_docs" in prompt


def test_kickoff_requires_at_least_one_source():
    with pytest.raises(ValueError, match="DROPBOX_ROOT"):
        build_kickoff(has_dropbox=False, has_mail=False)
