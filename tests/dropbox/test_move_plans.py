from pathlib import Path

import pytest

from src.dropbox.models.journal_action import JournalAction
from src.dropbox.models.move_plan_status import MovePlanStatus
from src.dropbox.models.planned_move import PlannedMove
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.entities.move_plan_status_error import MovePlanStatusError
from src.dropbox.services.move_executor.move_plan_executor import MovePlanExecutor
from src.dropbox.services.move_planner.move_planner import MovePlanner
from src.dropbox.services.move_rollback.move_plan_rollback import MovePlanRollback
from src.dropbox.services.move_validator.move_plan_validator import MovePlanValidator
from tests.dropbox.conftest import ITINERARY_NAME, tree_snapshot
from tests.dropbox.in_memory_dropbox_journal import InMemoryDropboxJournal
from tests.dropbox.in_memory_move_plan_store import InMemoryMovePlanStore

OWNER_ID = 42
TRAVEL = "03_home/09_travel/thailand_2026-11"


class MoveKit:
    def __init__(self, boundary: DropboxBoundary) -> None:
        self.plans = InMemoryMovePlanStore()
        self.journal = InMemoryDropboxJournal()
        validator = MovePlanValidator(boundary)
        self.planner = MovePlanner(validator, self.plans)
        self.executor = MovePlanExecutor(self.plans, validator, boundary, self.journal)
        self.rollback = MovePlanRollback(self.plans, boundary, self.journal)


@pytest.fixture
def kit(boundary: DropboxBoundary) -> MoveKit:
    return MoveKit(boundary)


def _moves(*pairs: tuple[str, str]) -> list[PlannedMove]:
    return [PlannedMove(source=source, target=target) for source, target in pairs]


def test_plan_with_occupied_target_is_rejected_whole(kit: MoveKit, dropbox_root: Path):
    before = tree_snapshot(dropbox_root)

    proposal = kit.planner.propose(
        OWNER_ID,
        _moves(
            (ITINERARY_NAME, f"{TRAVEL}/{ITINERARY_NAME}"),
            ("scan.pdf", "03_home/01_personal_docs/notes.md"),
        ),
    )

    assert proposal.plan is None
    assert [problem.move.source for problem in proposal.problems] == ["scan.pdf"]
    assert "занят" in proposal.problems[0].reason
    assert tree_snapshot(dropbox_root) == before
    assert kit.journal.entries == []


@pytest.mark.parametrize(
    ("source", "target", "reason_part"),
    [
        ("missing.pdf", "03_home/missing.pdf", "нет"),
        ("Apps/HealthFit/ride.fit", "03_home/ride.fit", "Apps/"),
        ("scan.pdf", "Apps/scan.pdf", "Apps/"),
        ("scan.pdf", "Vault/scan.pdf", "закрытая"),
        ("scan.pdf", "01_work/scan.pdf", "закрытая"),
        ("03_home/07_ecp/backup_AUTH.P12", "03_home/key.p12", "ключевой"),
        ("03_home/07_ecp", "07_ecp", "закрытое или ключевое"),
        ("03_home", "home", "закрытое или ключевое"),
        ("innocent.txt", "03_home/innocent.txt", "ссылка"),
        ("scan.pdf", "03_home/01_personal_docs/notes.md/scan.pdf", "файл"),
    ],
)
def test_plan_with_forbidden_move_is_rejected(
    kit: MoveKit, source: str, target: str, reason_part: str
):
    proposal = kit.planner.propose(OWNER_ID, _moves((source, target)))

    assert proposal.plan is None
    assert reason_part in proposal.problems[0].reason


def test_plan_with_conflicting_moves_is_rejected(kit: MoveKit):
    proposal = kit.planner.propose(
        OWNER_ID,
        _moves(("scan.pdf", "03_home/doc.pdf"), (ITINERARY_NAME, "03_home/doc.pdf")),
    )

    assert proposal.plan is None
    assert len(proposal.problems) == 2


def test_plan_executes_and_rolls_back_to_original_tree(
    kit: MoveKit, dropbox_root: Path
):
    before = tree_snapshot(dropbox_root)
    proposal = kit.planner.propose(
        OWNER_ID,
        _moves(
            (ITINERARY_NAME, f"{TRAVEL}/{ITINERARY_NAME}"),
            ("scan.pdf", "03_home/scans/2026/scan-renamed.pdf"),
            (
                "03_home/01_personal_docs/notes.md",
                "03_home/01_personal_docs/Заметки.md",
            ),
        ),
    )
    assert proposal.plan is not None
    assert proposal.plan.status == MovePlanStatus.PROPOSED
    plan_id = proposal.plan.id

    execution = kit.executor.execute(plan_id)

    assert execution.problems == []
    assert execution.plan.status == MovePlanStatus.EXECUTED
    assert (dropbox_root / TRAVEL / ITINERARY_NAME).is_file()
    assert (dropbox_root / "03_home/scans/2026/scan-renamed.pdf").is_file()
    assert not (dropbox_root / "scan.pdf").exists()
    assert [entry.action for entry in kit.journal.entries] == [JournalAction.MOVED] * 3

    result = kit.rollback.rollback(plan_id)

    assert result.skipped == []
    assert [move.source for move in result.rolled_back] == [
        "03_home/01_personal_docs/notes.md",
        "scan.pdf",
        ITINERARY_NAME,
    ]
    assert tree_snapshot(dropbox_root) == before
    assert result.plan.status == MovePlanStatus.ROLLED_BACK
    stored = kit.plans.get(plan_id)
    assert stored is not None
    assert stored.status == MovePlanStatus.ROLLED_BACK


def test_rollback_skips_move_whose_file_was_moved_by_hand_and_names_it(
    kit: MoveKit, dropbox_root: Path
):
    proposal = kit.planner.propose(
        OWNER_ID,
        _moves(
            (ITINERARY_NAME, f"{TRAVEL}/{ITINERARY_NAME}"),
            ("scan.pdf", "03_home/scan.pdf"),
        ),
    )
    assert proposal.plan is not None
    plan_id = proposal.plan.id
    kit.executor.execute(plan_id)
    (dropbox_root / TRAVEL / ITINERARY_NAME).rename(
        dropbox_root / TRAVEL / "ticket.pdf"
    )

    result = kit.rollback.rollback(plan_id)

    assert [move.source for move in result.rolled_back] == ["scan.pdf"]
    assert [problem.move.target for problem in result.skipped] == [
        f"{TRAVEL}/{ITINERARY_NAME}"
    ]
    assert f"{TRAVEL}/{ITINERARY_NAME}" in result.skipped[0].reason
    assert (dropbox_root / "scan.pdf").is_file()
    assert (dropbox_root / TRAVEL / "ticket.pdf").is_file()
    skipped_entries = [
        entry
        for entry in kit.journal.entries
        if entry.action == JournalAction.ROLLBACK_SKIPPED
    ]
    assert [entry.reason for entry in skipped_entries] == [result.skipped[0].reason]


def test_rollback_skips_move_whose_source_place_is_taken(
    kit: MoveKit, dropbox_root: Path
):
    proposal = kit.planner.propose(OWNER_ID, _moves(("scan.pdf", "03_home/scan.pdf")))
    assert proposal.plan is not None
    kit.executor.execute(proposal.plan.id)
    (dropbox_root / "scan.pdf").write_bytes(b"new scan")

    result = kit.rollback.rollback(proposal.plan.id)

    assert result.rolled_back == []
    assert "занят" in result.skipped[0].reason
    assert (dropbox_root / "scan.pdf").read_bytes() == b"new scan"


def test_execution_rechecks_plan_and_moves_nothing_if_target_got_occupied(
    kit: MoveKit, dropbox_root: Path
):
    proposal = kit.planner.propose(
        OWNER_ID,
        _moves(
            (ITINERARY_NAME, f"{TRAVEL}/{ITINERARY_NAME}"),
            ("scan.pdf", "03_home/scan.pdf"),
        ),
    )
    assert proposal.plan is not None
    (dropbox_root / "03_home" / "scan.pdf").write_bytes(b"appeared meanwhile")
    before = tree_snapshot(dropbox_root)

    execution = kit.executor.execute(proposal.plan.id)

    assert execution.moved == []
    assert [problem.move.source for problem in execution.problems] == ["scan.pdf"]
    assert tree_snapshot(dropbox_root) == before
    assert execution.plan.status == MovePlanStatus.PROPOSED


def test_plan_is_executed_and_rolled_back_only_once(kit: MoveKit):
    proposal = kit.planner.propose(OWNER_ID, _moves(("scan.pdf", "03_home/scan.pdf")))
    assert proposal.plan is not None
    plan_id = proposal.plan.id
    kit.executor.execute(plan_id)

    with pytest.raises(MovePlanStatusError):
        kit.executor.execute(plan_id)
    kit.rollback.rollback(plan_id)
    with pytest.raises(MovePlanStatusError):
        kit.rollback.rollback(plan_id)
