import psycopg
from psycopg.rows import class_row

from src.scheduled_runs.models.scheduled_run import ScheduledRun


class PostgresScheduledRunRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def start(self, run_id: str, schedule_id: str, case_id: str) -> ScheduledRun:
        with (
            psycopg.connect(self._database_url) as connection,
            connection.cursor(row_factory=class_row(ScheduledRun)) as cursor,
        ):
            cursor.execute(
                """
                INSERT INTO scheduled_runs (run_id, schedule_id, case_id)
                VALUES (%(run_id)s, %(schedule_id)s, %(case_id)s)
                ON CONFLICT (run_id) DO NOTHING
                """,
                {"run_id": run_id, "schedule_id": schedule_id, "case_id": case_id},
            )
            cursor.execute(
                """
                SELECT id, run_id, schedule_id, case_id, started_at,
                       finished_at, delivered_at, error
                FROM scheduled_runs
                WHERE run_id = %(run_id)s
                """,
                {"run_id": run_id},
            )
            stored = cursor.fetchone()
        if stored is None:
            raise LookupError(f"Scheduled run {run_id} was not stored")
        return stored

    def finish(self, run_id: str, error: str | None) -> None:
        with psycopg.connect(self._database_url) as connection:
            connection.execute(
                """
                UPDATE scheduled_runs
                SET finished_at = NOW(), error = %(error)s
                WHERE run_id = %(run_id)s
                """,
                {"run_id": run_id, "error": error},
            )

    def mark_delivered(self, run_id: str) -> None:
        with psycopg.connect(self._database_url) as connection:
            connection.execute(
                """
                UPDATE scheduled_runs
                SET delivered_at = NOW()
                WHERE run_id = %(run_id)s
                """,
                {"run_id": run_id},
            )
