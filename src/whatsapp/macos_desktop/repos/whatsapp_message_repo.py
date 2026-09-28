from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow
from src.whatsapp.macos_desktop.repos.snapshot_database import SnapshotDatabase

SEARCH_SQL = """
SELECT * FROM visible_message
WHERE (:text = '' OR contains_ci(body, :text))
  AND (:chat_pk IS NULL OR chat_pk = :chat_pk)
  AND (
      :participant IS NULL
      OR contains_ci(chat_title, :participant)
      OR contains_ci(push_name, :participant)
      OR contains_ci(member_name, :participant)
      OR contains_ci(member_first_name, :participant)
      OR contains_ci(sender_jid, :participant)
      OR contains_ci(chat_jid, :participant)
  )
  AND (:since IS NULL OR sent_at >= :since)
  AND (:until IS NULL OR sent_at < :until)
ORDER BY sent_at DESC, message_pk DESC
LIMIT :limit
"""

BY_PK_SQL = "SELECT * FROM visible_message WHERE message_pk = ?"

IN_CHAT_SQL = """
SELECT * FROM visible_message
WHERE chat_pk = :chat_pk
  AND (:since IS NULL OR sent_at >= :since)
  AND (:until IS NULL OR sent_at < :until)
ORDER BY sent_at DESC, message_pk DESC
LIMIT :limit
"""

HAS_BEFORE_SQL = """
SELECT EXISTS (
    SELECT 1 FROM visible_message
    WHERE chat_pk = :chat_pk
      AND (sent_at < :sent_at OR (sent_at = :sent_at AND message_pk < :message_pk))
)
"""

LAST_MESSAGE_SQL = "SELECT MAX(ZMESSAGEDATE) FROM ZWAMESSAGE"


class WhatsAppMessageRepo:
    def __init__(self, database: SnapshotDatabase) -> None:
        self._database = database

    def search(
        self,
        text: str,
        chat_pk: int | None,
        participant: str | None,
        since: float | None,
        until: float | None,
        limit: int,
    ) -> list[WhatsAppMessageRow]:
        parameters = {
            "text": text,
            "chat_pk": chat_pk,
            "participant": participant,
            "since": since,
            "until": until,
            "limit": limit,
        }
        with self._database.connect() as connection:
            rows = connection.execute(SEARCH_SQL, parameters).fetchall()
        return [WhatsAppMessageRow(**dict(row)) for row in rows]

    def by_pk(self, message_pk: int) -> WhatsAppMessageRow | None:
        with self._database.connect() as connection:
            row = connection.execute(BY_PK_SQL, (message_pk,)).fetchone()
        return None if row is None else WhatsAppMessageRow(**dict(row))

    def in_chat(
        self, chat_pk: int, since: float | None, until: float | None, limit: int
    ) -> list[WhatsAppMessageRow]:
        parameters = {
            "chat_pk": chat_pk,
            "since": since,
            "until": until,
            "limit": limit,
        }
        with self._database.connect() as connection:
            rows = connection.execute(IN_CHAT_SQL, parameters).fetchall()
        return [WhatsAppMessageRow(**dict(row)) for row in reversed(rows)]

    def has_before(self, chat_pk: int, sent_at: float, message_pk: int) -> bool:
        parameters = {"chat_pk": chat_pk, "sent_at": sent_at, "message_pk": message_pk}
        with self._database.connect() as connection:
            row = connection.execute(HAS_BEFORE_SQL, parameters).fetchone()
        return bool(row[0])

    def last_message_seconds(self) -> float | None:
        with self._database.connect() as connection:
            row = connection.execute(LAST_MESSAGE_SQL).fetchone()
        return None if row[0] is None else float(row[0])
