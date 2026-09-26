from datetime import date
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from ai_framework import AIResponse, BaseTool, Message, ToolCall
from ai_framework.memory.in_memory_store import InMemoryStore
from ai_framework.session.in_memory_session_store import InMemorySessionStore
from ai_framework.tool_loop import ToolLoop
from ai_framework.tools.tool_registry_factory import create_tool_registry

from bot_framework.core.entities.parse_mode import ParseMode
from src.checkup.repos import CheckupJournalRepository
from src.gmail.models.mail_message import MailMessage
from src.gmail.models.mail_summary import MailSummary
from src.todoist.models import TodoistDue, TodoistProject, TodoistTask
from src.todoist.services.todoist_task_service import TodoistTaskService
from tests.memory.in_memory_wiki_storage import InMemoryWikiStorage
from workers.checkup.checkup_pass import CheckupPass
from workers.checkup.composition import (
    CHECKUP_PROMPT_PATH,
    build_checkup_actions,
    build_checkup_system_prompt,
    build_checkup_tools,
)
from workers.checkup.report_delivery import ReportDelivery
from workers.memory_fill.composition import (
    build_kickoff,
    build_memory_fill_run,
    build_memory_fill_tools,
)
from workers.memory_fill.owner_notifier import OwnerNotifier

TIMEZONE = ZoneInfo("Asia/Almaty")
TODAY = date(2026, 9, 26)
DEPARTURE = date(2026, 11, 12)
OWNER_CHAT_ID = 42
EDS_PATH = "03_home/01_personal_docs/ЭЦП Владимир.txt"
TICKET_ID = "18c1a"
EDS_KEY = "ЭЦП РК | Владимир | 20.11.2026"
REASON = (
    "ЭЦП истекает 20.11.2026, продлить можно только в РК, а с 12.11.2026 ты в Чиангмае"
)

FILL_SCRIPT: list[tuple[str, dict[str, object]]] = [
    ("memory_show", {"page": "all"}),
    ("dropbox_read", {"path": EDS_PATH}),
    ("search_mail", {"query": "newer_than:1y itinerary"}),
    ("read_mail", {"message_id": TICKET_ID}),
    (
        "memory_upsert_deadline",
        {
            "what": "ЭЦП РК",
            "whose": "Владимир",
            "expires": "2026-11-20",
            "renewal": "только в РК: ЦОН или eGov",
            "source": EDS_PATH,
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

CHECKUP_SCRIPT: list[tuple[str, dict[str, object]]] = [
    ("memory_show", {"page": "all"}),
    ("find_tasks", {"query": "@pa"}),
    ("find_tasks", {"query": "search: ЭЦП"}),
    (
        "checkup_create_task",
        {
            "key": EDS_KEY,
            "content": "Продлить ЭЦП РК до вылета в Чиангмай",
            "due": "2026-11-09",
            "reason": REASON,
        },
    ),
]


class ScriptedProvider:
    def __init__(self, script: list[tuple[str, dict[str, object]]]) -> None:
        self._script = script
        self._step = 0
        self.tool_results: dict[str, list[str]] = {}

    def send_message(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[BaseTool] | None = None,
        tool_context: dict[str, Any] | None = None,
    ) -> AIResponse:
        self._record_results(messages)
        if self._step == len(self._script):
            return AIResponse(content="Готово.")
        name, arguments = self._script[self._step]
        self._step += 1
        return AIResponse(
            tool_calls=[
                ToolCall(id=f"call-{self._step}", name=name, arguments=arguments)
            ]
        )

    def _record_results(self, messages: list[Message]) -> None:
        last = messages[-1]
        if not last.tool_results:
            return
        name, _ = self._script[self._step - 1]
        for result in last.tool_results:
            assert not result.is_error, result.content
            self.tool_results.setdefault(name, []).append(result.content)


class LoopConversation:
    def __init__(self, provider: ScriptedProvider, tools: list[BaseTool]) -> None:
        self._loop = ToolLoop(
            provider=provider,
            memory=InMemoryStore(),
            sessions=InMemorySessionStore(),
            tool_registry=create_tool_registry(tools),
            system_prompt="test",
            max_rounds=len(FILL_SCRIPT) + len(CHECKUP_SCRIPT) + 2,
        )

    def process_message(
        self,
        thread_id: str,
        user_message: str,
        tool_context: dict[str, Any] | None = None,
    ) -> AIResponse:
        return self._loop.run(thread_id, user_message, tool_context)


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


class FakeTodoist:
    def __init__(self) -> None:
        self.tasks: list[TodoistTask] = []

    def filter_tasks(self, query: str, limit: int) -> list[TodoistTask]:
        if query == "@pa":
            return [task for task in self.tasks if "pa" in task.labels][:limit]
        text = query.removeprefix("search:").strip().casefold()
        return [task for task in self.tasks if text in task.content.casefold()][:limit]

    def list_projects(self) -> list[TodoistProject]:
        return [TodoistProject(id="inbox", name="Inbox")]

    def add_task(
        self,
        content: str,
        due_string: str,
        due_lang: str,
        labels: list[str],
        description: str | None = None,
    ) -> TodoistTask:
        task = TodoistTask(
            id=f"task-{len(self.tasks) + 1}",
            content=content,
            description=description or "",
            project_id="inbox",
            labels=labels,
            due=TodoistDue(date=due_string, string=due_string),
        )
        self.tasks.append(task)
        return task


class FakeTelegram:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    def send(
        self, chat_id: int, text: str, parse_mode: ParseMode = ParseMode.PLAIN
    ) -> object:
        self.sent.append((chat_id, text))
        return None


class CheckupWorld:
    def __init__(self, dropbox_root: Path) -> None:
        self.dropbox_root = dropbox_root
        self.wiki = InMemoryWikiStorage()
        self.todoist = FakeTodoist()
        self.telegram = FakeTelegram()
        self.checkup_provider = ScriptedProvider(CHECKUP_SCRIPT)

    def run(self) -> None:
        fill_tools = build_memory_fill_tools(
            self.dropbox_root, FakeMailbox(), self.wiki, TIMEZONE
        )
        memory_fill = build_memory_fill_run(
            LoopConversation(ScriptedProvider(FILL_SCRIPT), fill_tools),
            self.wiki,
            build_kickoff(has_dropbox=True, has_mail=True),
            "memory_fill:test",
        )
        tasks = TodoistTaskService(self.todoist)
        actions = build_checkup_actions(self.wiki, tasks, lambda: TODAY)
        self.checkup_provider = ScriptedProvider(CHECKUP_SCRIPT)
        checkup = CheckupPass(
            memory_fill=memory_fill,
            conversation=LoopConversation(
                self.checkup_provider, build_checkup_tools(self.wiki, tasks, actions)
            ),
            thread_id="checkup:test",
        )
        report = checkup.execute()
        ReportDelivery(OwnerNotifier(self.telegram, OWNER_CHAT_ID)).deliver(report)


@pytest.fixture
def world(tmp_path: Path) -> CheckupWorld:
    documents = tmp_path / "Dropbox" / "03_home" / "01_personal_docs"
    documents.mkdir(parents=True)
    (documents / "ЭЦП Владимир.txt").write_text(
        "ЭЦП РК, Владимир, действует до 20.11.2026. Продление только в РК.",
        encoding="utf-8",
    )
    return CheckupWorld(tmp_path / "Dropbox")


def test_checkup_sets_task_before_departure_and_messages_owner(world: CheckupWorld):
    world.run()

    assert len(world.todoist.tasks) == 1
    task = world.todoist.tasks[0]
    assert task.labels == ["pa"]
    assert task.due is not None
    assert date.fromisoformat(task.due.date) <= DEPARTURE
    assert len(world.telegram.sent) == 1
    chat_id, text = world.telegram.sent[0]
    assert chat_id == OWNER_CHAT_ID
    assert "Продлить ЭЦП РК до вылета в Чиангмай — до 09.11.2026" in text
    assert REASON in text


def test_second_checkup_neither_duplicates_task_nor_messages(world: CheckupWorld):
    world.run()

    world.run()

    assert len(world.todoist.tasks) == 1
    assert len(world.telegram.sent) == 1
    assert (
        "already_done" in world.checkup_provider.tool_results["checkup_create_task"][0]
    )
    assert "task-1" in world.checkup_provider.tool_results["find_tasks"][0]
    journal = CheckupJournalRepository(world.wiki)
    assert journal.find(EDS_KEY) is not None


def test_checkup_prompt_renders_without_unfilled_placeholders():
    prompt = build_checkup_system_prompt(
        CHECKUP_PROMPT_PATH.read_text(encoding="utf-8"), TIMEZONE
    )

    assert "{" not in prompt
    assert "find_tasks" in prompt
