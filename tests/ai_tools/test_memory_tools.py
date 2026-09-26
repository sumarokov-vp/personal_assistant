import json
from datetime import date
from zoneinfo import ZoneInfo

from ai_framework.entities.tool_context import ToolContext

from src.ai_tools import (
    MemoryCloseCommitmentTool,
    MemoryShowTool,
    MemoryUpsertCommitmentTool,
    MemoryUpsertDeadlineTool,
    MemoryUpsertTripTool,
)
from src.ai_tools.memory_close_commitment.tool import MemoryCloseCommitmentInput
from src.ai_tools.memory_show.tool import MemoryShowInput
from src.ai_tools.memory_upsert_commitment.tool import MemoryUpsertCommitmentInput
from src.ai_tools.memory_upsert_deadline.tool import MemoryUpsertDeadlineInput
from src.ai_tools.memory_upsert_trip.tool import MemoryUpsertTripInput
from src.memory.models import Commitment, CommitmentStatus, Deadline
from src.memory.repos import (
    CommitmentRepository,
    DeadlineRepository,
    WhereaboutsRepository,
)
from src.wiki import WikiPageChangedError
from tests.memory.in_memory_wiki_storage import InMemoryWikiStorage

DEADLINES = "Assistant/Реестр сроков.md"
CONTEXT = ToolContext({"chat_id": 1, "user_id": 1})
TIMEZONE = ZoneInfo("Asia/Almaty")


class ConflictingStorage(InMemoryWikiStorage):
    def write(self, path: str, content: str, commit_message: str) -> None:
        raise WikiPageChangedError()


def _passport_storage() -> InMemoryWikiStorage:
    storage = InMemoryWikiStorage()
    DeadlineRepository(storage).upsert(
        Deadline(
            what="Паспорт РФ",
            whose="Владимир",
            expires=date(2026, 3, 1),
            renewal="МФЦ",
            source="Dropbox/Документы",
        )
    )
    return storage


def test_upsert_deadline_keeps_fields_not_mentioned_in_dialog():
    storage = _passport_storage()
    tool = MemoryUpsertDeadlineTool(DeadlineRepository(storage), TIMEZONE)

    reply = json.loads(
        tool.execute(
            MemoryUpsertDeadlineInput(
                what="паспорт РФ",
                whose="Владимир",
                expires=date(2036, 3, 1),
                source="диалог",
            ),
            CONTEXT,
        )
    )

    assert reply["status"] == "updated"
    assert reply["page"] == DEADLINES
    assert reply["entry"]["expires"] == "01.03.2036"
    assert reply["entry"]["renewal"] == "МФЦ"
    entries = DeadlineRepository(storage).read().entries
    assert len(entries) == 1
    assert entries[0].source == "диалог"
    assert entries[0].updated is not None


def test_upsert_trip_then_show_all_pages():
    storage = InMemoryWikiStorage()
    whereabouts = WhereaboutsRepository(storage)
    trip_tool = MemoryUpsertTripTool(whereabouts)
    trip_tool.execute(
        MemoryUpsertTripInput(since=date(2026, 11, 12), place="Чиангмай"), CONTEXT
    )

    reply = json.loads(
        trip_tool.execute(
            MemoryUpsertTripInput(
                since=date(2026, 11, 12), place="чиангмай", until=date(2027, 2, 12)
            ),
            CONTEXT,
        )
    )
    shown = json.loads(
        MemoryShowTool(
            DeadlineRepository(storage), whereabouts, CommitmentRepository(storage)
        ).execute(MemoryShowInput(), CONTEXT)
    )

    assert reply["status"] == "updated"
    pages = {page["page"]: page for page in shown["pages"]}
    assert pages[DEADLINES]["entries"] == []
    trips = pages["Assistant/Где я буду.md"]["entries"]
    assert [(trip["since"], trip["until"]) for trip in trips] == [
        ("12.11.2026", "12.02.2027")
    ]


def test_close_commitment_keeps_row_and_reports_missing():
    storage = InMemoryWikiStorage()
    commitments = CommitmentRepository(storage)
    MemoryUpsertCommitmentTool(commitments).execute(
        MemoryUpsertCommitmentInput(what="Прислать акт", parties="я → бухгалтер"),
        CONTEXT,
    )
    close_tool = MemoryCloseCommitmentTool(commitments)

    closed = json.loads(
        close_tool.execute(
            MemoryCloseCommitmentInput(what="прислать акт", parties="я → бухгалтер"),
            CONTEXT,
        )
    )
    missing = json.loads(
        close_tool.execute(
            MemoryCloseCommitmentInput(what="Другое", parties="я → бухгалтер"), CONTEXT
        )
    )

    assert closed["status"] == "closed"
    assert closed["entry"]["status"] == "выполнено"
    assert missing["status"] == "not_found"
    assert commitments.read().entries == [
        Commitment(
            what="Прислать акт", parties="я → бухгалтер", status=CommitmentStatus.DONE
        )
    ]


def test_renamed_column_and_wiki_conflict_become_error_text():
    renamed = InMemoryWikiStorage({DEADLINES: "| Документ | Чьё |\n|---|---|\n"})
    conflicting = ConflictingStorage()
    request = MemoryUpsertDeadlineInput(
        what="ЭЦП РК", whose="Владимир", expires=date(2027, 1, 5)
    )

    format_error = json.loads(
        MemoryUpsertDeadlineTool(DeadlineRepository(renamed), TIMEZONE).execute(
            request, CONTEXT
        )
    )
    conflict = json.loads(
        MemoryUpsertDeadlineTool(DeadlineRepository(conflicting), TIMEZONE).execute(
            request, CONTEXT
        )
    )

    assert format_error["status"] == "error"
    assert "колонки" in format_error["message"]
    assert renamed.commits == []
    assert conflict["status"] == "error"
    assert "повтори" in conflict["message"]
