from datetime import date

import pytest

from src.memory.models import Commitment, CommitmentStatus, Deadline, Whereabouts
from src.memory.repos import (
    CommitmentRepository,
    DeadlineRepository,
    MemoryPageFormatError,
    UpsertOutcome,
    WhereaboutsRepository,
)
from tests.memory.in_memory_wiki_storage import InMemoryWikiStorage

DEADLINES = "Assistant/Реестр сроков.md"
WHEREABOUTS = "Assistant/Где я буду.md"
COMMITMENTS = "Assistant/Обязательства.md"

HAND_EDITED_DEADLINES = """Ведёт ассистент, колонки не переименовывать.

Заметка владельца над таблицей.

|  Что | Чьё  | Истекает | Где и как продлевать | Сколько занимает | Источник | Обновлено |
|---|---|---|---|---|---|---|
| Паспорт РФ  |   Владимир | 01.03.2031 | МФЦ | месяц | Dropbox/Документы | 20.09.2026 |
| ЭЦП РК | Владимир | 5.1.2027 | egov.kz \\| ЦОН | день | диалог | |
| Страховка | Анна | скоро | | | почта | |
| сломанная строка без ячеек
| Водительское | Анна | 10.10.2029 | ГАИ | неделя | Dropbox/Права | 20.09.2026 | лишнее |

Хвост страницы после таблицы.
"""


def test_hand_edited_page_is_read_without_losing_rows():
    storage = InMemoryWikiStorage({DEADLINES: HAND_EDITED_DEADLINES})

    read = DeadlineRepository(storage).read()

    assert [(entry.what, entry.whose, entry.expires) for entry in read.entries] == [
        ("Паспорт РФ", "Владимир", date(2031, 3, 1)),
        ("ЭЦП РК", "Владимир", date(2027, 1, 5)),
    ]
    assert read.entries[1].renewal == "egov.kz | ЦОН"
    assert len(read.remarks) == 3
    assert "Страховка" in read.remarks[0]


def test_upsert_on_hand_edited_page_keeps_foreign_rows_and_surroundings():
    storage = InMemoryWikiStorage({DEADLINES: HAND_EDITED_DEADLINES})
    repository = DeadlineRepository(storage)

    repository.upsert(
        Deadline(what="Паспорт РФ", whose="Владимир", expires=date(2036, 3, 1))
    )

    written = storage.files[DEADLINES]
    for kept in (
        "Заметка владельца над таблицей.",
        "| Страховка | Анна | скоро | | | почта | |",
        "| сломанная строка без ячеек",
        "Хвост страницы после таблицы.",
    ):
        assert kept in written
    assert len(repository.read().entries) == 2


def test_upsert_by_key_replaces_one_row_instead_of_adding_duplicate():
    storage = InMemoryWikiStorage({DEADLINES: HAND_EDITED_DEADLINES})
    repository = DeadlineRepository(storage)

    outcome = repository.upsert(
        Deadline(
            what=" паспорт  рф",
            whose="ВЛАДИМИР",
            expires=date(2036, 3, 1),
            updated=date(2026, 9, 26),
        )
    )

    entries = repository.read().entries
    assert outcome is UpsertOutcome.UPDATED
    assert len(entries) == 2
    assert entries[0].expires == date(2036, 3, 1)
    assert entries[1].what == "ЭЦП РК"
    assert (
        storage.commits[-1][1]
        == "память: Реестр сроков — обновлено «паспорт рф · ВЛАДИМИР»"
    )


def test_upsert_with_new_key_appends_row():
    storage = InMemoryWikiStorage({DEADLINES: HAND_EDITED_DEADLINES})
    repository = DeadlineRepository(storage)

    outcome = repository.upsert(
        Deadline(what="Паспорт РФ", whose="Анна", expires=date(2030, 1, 1))
    )

    assert outcome is UpsertOutcome.CREATED
    assert len(repository.read().entries) == 3


def test_missing_page_is_created_with_note_and_table():
    storage = InMemoryWikiStorage()

    WhereaboutsRepository(storage).upsert(
        Whereabouts(
            since=date(2026, 11, 12),
            until=date(2027, 2, 12),
            place="Чиангмай",
            purpose="зимовка",
        )
    )

    assert storage.files[WHEREABOUTS] == (
        "Ведёт ассистент, колонки не переименовывать.\n"
        "\n"
        "| С | По | Где | Что | Источник |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 12.11.2026 | 12.02.2027 | Чиангмай | зимовка |  |\n"
    )


def test_render_then_parse_returns_same_entries():
    storage = InMemoryWikiStorage()
    repository = CommitmentRepository(storage)
    commitments = [
        Commitment(
            what="Вернуть долг | часть",
            parties="я → Иван",
            due=date(2026, 10, 1),
            source="почта",
        ),
        Commitment(
            what="Прислать акт",
            parties="Бухгалтер → я",
            status=CommitmentStatus.CANCELLED,
        ),
    ]

    for commitment in commitments:
        repository.upsert(commitment)

    assert repository.read().entries == commitments
    assert repository.read().remarks == []


def test_close_marks_commitment_done_without_removing_it():
    storage = InMemoryWikiStorage()
    repository = CommitmentRepository(storage)
    repository.upsert(Commitment(what="Прислать акт", parties="Бухгалтер → я"))

    closed = repository.close("прислать акт", "бухгалтер → я")

    assert closed is not None
    assert repository.read().entries == [closed]
    assert closed.status is CommitmentStatus.DONE
    assert repository.close("Чего нет", "никто") is None


def test_upsert_refuses_page_whose_table_columns_were_renamed():
    storage = InMemoryWikiStorage(
        {COMMITMENTS: "| Задача | Кто | Срок |\n|---|---|---|\n| a | b | |\n"}
    )

    with pytest.raises(MemoryPageFormatError):
        CommitmentRepository(storage).upsert(Commitment(what="x", parties="y"))

    assert storage.commits == []
