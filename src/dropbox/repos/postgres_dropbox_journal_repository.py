from uuid import UUID

import psycopg
from psycopg.rows import class_row

from src.dropbox.models.journal_entry import JournalEntry


class PostgresDropboxJournalRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def append(self, entry: JournalEntry) -> None:
        with psycopg.connect(self._database_url) as connection:
            connection.execute(
                """
                INSERT INTO dropbox_journal
                    (plan_id, action, source, target, reason, created_at)
                VALUES
                    (%(plan_id)s, %(action)s, %(source)s, %(target)s,
                     %(reason)s, %(created_at)s)
                """,
                {
                    "plan_id": entry.plan_id,
                    "action": entry.action.value,
                    "source": entry.source,
                    "target": entry.target,
                    "reason": entry.reason,
                    "created_at": entry.created_at,
                },
            )

    def plan_entries(self, plan_id: UUID) -> list[JournalEntry]:
        with (
            psycopg.connect(self._database_url) as connection,
            connection.cursor(row_factory=class_row(JournalEntry)) as cursor,
        ):
            cursor.execute(
                """
                SELECT action, plan_id, source, target, reason, created_at
                FROM dropbox_journal
                WHERE plan_id = %(plan_id)s
                ORDER BY id
                """,
                {"plan_id": plan_id},
            )
            return cursor.fetchall()
