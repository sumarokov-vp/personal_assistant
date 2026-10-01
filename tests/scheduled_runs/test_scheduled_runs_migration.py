import os
from pathlib import Path

import psycopg
import pytest
from yoyo import get_backend, read_migrations

from src.app_migrations import apply_migrations
from src.scheduled_runs.repos import PostgresScheduledRunRepository

MIGRATIONS_DIR = Path(__file__).parents[2] / "src" / "app_migrations" / "sql"
SCHEDULED_RUNS_MIGRATION = "0005.pa_scheduled_runs"


@pytest.fixture
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set: migration test needs real Postgres")
    apply_migrations(url)
    return url


def _rollback_scheduled_runs(database_url: str) -> None:
    backend = get_backend(
        database_url.replace("postgres://", "postgresql+psycopg://", 1)
    )
    migrations = read_migrations(str(MIGRATIONS_DIR)).filter(
        lambda migration: migration.id == SCHEDULED_RUNS_MIGRATION
    )
    with backend.lock():
        backend.rollback_migrations(backend.to_rollback(migrations))


def _has_table(database_url: str) -> bool:
    with psycopg.connect(database_url) as connection:
        row = connection.execute("SELECT to_regclass('scheduled_runs')").fetchone()
    return row is not None and row[0] is not None


def test_journal_keeps_one_run_per_run_id_and_migration_rolls_back(database_url: str):
    journal = PostgresScheduledRunRepository(database_url)

    first = journal.start("run-1", "schedule-1", "case-1")
    journal.finish("run-1", "TimeoutError")
    journal.mark_delivered("run-1")
    again = journal.start("run-1", "schedule-1", "case-1")

    assert again.id == first.id
    assert again.error == "TimeoutError"
    assert again.finished_at is not None
    assert again.delivered_at is not None

    _rollback_scheduled_runs(database_url)
    assert not _has_table(database_url)

    assert apply_migrations(database_url) == 1
    assert _has_table(database_url)
    assert journal.start("run-1", "schedule-1", "case-1").delivered_at is None
