from datetime import datetime

import psycopg

from src.colleague_mail.models.colleague_message_type import ColleagueMessageType
from src.colleague_mail.models.message_direction import MessageDirection


class PostgresColleagueMessageRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def record_incoming(
        self,
        message_id: str,
        sender: str,
        message_type: ColleagueMessageType,
        text: str,
        about_agent: str | None,
        in_reply_to: str | None,
        sent_at: datetime | None,
    ) -> bool:
        return self._insert(
            message_id=message_id,
            direction=MessageDirection.INCOMING,
            peer=sender,
            message_type=message_type,
            text=text,
            about_agent=about_agent,
            in_reply_to=in_reply_to,
            sent_at=sent_at,
        )

    def record_outgoing(
        self,
        message_id: str,
        recipient: str,
        message_type: ColleagueMessageType,
        text: str,
        about_agent: str | None,
        in_reply_to: str | None,
        sent_at: datetime,
    ) -> None:
        self._insert(
            message_id=message_id,
            direction=MessageDirection.OUTGOING,
            peer=recipient,
            message_type=message_type,
            text=text,
            about_agent=about_agent,
            in_reply_to=in_reply_to,
            sent_at=sent_at,
        )

    def _insert(
        self,
        message_id: str,
        direction: MessageDirection,
        peer: str,
        message_type: ColleagueMessageType,
        text: str,
        about_agent: str | None,
        in_reply_to: str | None,
        sent_at: datetime | None,
    ) -> bool:
        with psycopg.connect(self._database_url) as connection:
            inserted = connection.execute(
                """
                INSERT INTO colleague_messages
                    (message_id, direction, peer, type, text, about_agent,
                     in_reply_to, sent_at, received_at)
                VALUES
                    (%(message_id)s, %(direction)s, %(peer)s, %(type)s, %(text)s,
                     %(about_agent)s, %(in_reply_to)s, %(sent_at)s,
                     CASE WHEN %(direction)s = 'in' THEN NOW() END)
                ON CONFLICT (message_id, direction) DO NOTHING
                RETURNING id
                """,
                {
                    "message_id": message_id,
                    "direction": direction.value,
                    "peer": peer,
                    "type": message_type.value,
                    "text": text,
                    "about_agent": about_agent,
                    "in_reply_to": in_reply_to,
                    "sent_at": sent_at,
                },
            ).fetchone()
        return inserted is not None
