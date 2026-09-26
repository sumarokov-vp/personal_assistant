from datetime import datetime

import psycopg
from psycopg.rows import class_row

from src.agent_notifications.models.agent_notification import AgentNotification


class PostgresAgentNotificationRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def record(
        self,
        message_id: str,
        source: str,
        body: str,
        published_at: datetime | None,
    ) -> AgentNotification:
        with (
            psycopg.connect(self._database_url) as connection,
            connection.cursor(row_factory=class_row(AgentNotification)) as cursor,
        ):
            cursor.execute(
                """
                INSERT INTO agent_notifications
                    (message_id, source, body, published_at)
                VALUES
                    (%(message_id)s, %(source)s, %(body)s, %(published_at)s)
                ON CONFLICT (message_id) DO NOTHING
                """,
                {
                    "message_id": message_id,
                    "source": source,
                    "body": body,
                    "published_at": published_at,
                },
            )
            cursor.execute(
                """
                SELECT id, message_id, source, body, published_at,
                       received_at, delivered_at
                FROM agent_notifications
                WHERE message_id = %(message_id)s
                """,
                {"message_id": message_id},
            )
            stored = cursor.fetchone()
        if stored is None:
            raise LookupError(f"Agent notification {message_id} was not stored")
        return stored

    def mark_delivered(self, message_id: str) -> None:
        with psycopg.connect(self._database_url) as connection:
            connection.execute(
                """
                UPDATE agent_notifications
                SET delivered_at = NOW()
                WHERE message_id = %(message_id)s
                """,
                {"message_id": message_id},
            )

    def received_between(
        self,
        start: datetime,
        end: datetime,
        source: str | None,
        limit: int,
    ) -> list[AgentNotification]:
        with (
            psycopg.connect(self._database_url) as connection,
            connection.cursor(row_factory=class_row(AgentNotification)) as cursor,
        ):
            cursor.execute(
                """
                SELECT id, message_id, source, body, published_at,
                       received_at, delivered_at
                FROM agent_notifications
                WHERE received_at >= %(start)s AND received_at < %(end)s
                  AND (%(source)s::text IS NULL OR source = %(source)s)
                ORDER BY received_at DESC, id DESC
                LIMIT %(limit)s
                """,
                {"start": start, "end": end, "source": source, "limit": limit},
            )
            return cursor.fetchall()
