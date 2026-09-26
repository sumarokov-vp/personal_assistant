from uuid import UUID

import psycopg
from psycopg.rows import class_row
from psycopg.types.json import Jsonb

from src.dropbox.models.move_plan import MovePlan
from src.dropbox.models.move_plan_status import MovePlanStatus


class PostgresMovePlanRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def add(self, plan: MovePlan) -> None:
        with psycopg.connect(self._database_url) as connection:
            connection.execute(
                """
                INSERT INTO dropbox_move_plans
                    (id, owner_id, status, moves, created_at, updated_at)
                VALUES
                    (%(id)s, %(owner_id)s, %(status)s, %(moves)s,
                     %(created_at)s, %(updated_at)s)
                """,
                {
                    "id": plan.id,
                    "owner_id": plan.owner_id,
                    "status": plan.status.value,
                    "moves": Jsonb([move.model_dump() for move in plan.moves]),
                    "created_at": plan.created_at,
                    "updated_at": plan.updated_at,
                },
            )

    def get(self, plan_id: UUID) -> MovePlan | None:
        with (
            psycopg.connect(self._database_url) as connection,
            connection.cursor(row_factory=class_row(MovePlan)) as cursor,
        ):
            cursor.execute(
                """
                SELECT id, owner_id, status, moves, created_at, updated_at
                FROM dropbox_move_plans
                WHERE id = %(id)s
                """,
                {"id": plan_id},
            )
            return cursor.fetchone()

    def update_status(self, plan_id: UUID, status: MovePlanStatus) -> None:
        with psycopg.connect(self._database_url) as connection:
            connection.execute(
                """
                UPDATE dropbox_move_plans
                SET status = %(status)s, updated_at = NOW()
                WHERE id = %(id)s
                """,
                {"id": plan_id, "status": status.value},
            )
