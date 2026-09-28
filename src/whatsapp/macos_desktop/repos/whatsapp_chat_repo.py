from src.whatsapp.macos_desktop.models.whatsapp_chat_row import WhatsAppChatRow
from src.whatsapp.macos_desktop.repos.snapshot_database import SnapshotDatabase

CHAT_COLUMNS = """
SELECT
    Z_PK AS chat_pk,
    ZPARTNERNAME AS title,
    ZCONTACTJID AS jid,
    ZSESSIONTYPE AS session_type,
    ZLASTMESSAGEDATE AS last_message_at
FROM ZWACHATSESSION
"""

BY_PK_SQL = CHAT_COLUMNS + "WHERE Z_PK = ?"

LIST_SQL = (
    CHAT_COLUMNS
    + """
WHERE :title IS NULL
   OR contains_ci(ZPARTNERNAME, :title)
   OR contains_ci(ZCONTACTJID, :title)
ORDER BY ZLASTMESSAGEDATE IS NULL, ZLASTMESSAGEDATE DESC, Z_PK DESC
LIMIT :limit
"""
)


class WhatsAppChatRepo:
    def __init__(self, database: SnapshotDatabase) -> None:
        self._database = database

    def by_pk(self, chat_pk: int) -> WhatsAppChatRow | None:
        with self._database.connect() as connection:
            row = connection.execute(BY_PK_SQL, (chat_pk,)).fetchone()
        return None if row is None else WhatsAppChatRow(**dict(row))

    def list_chats(
        self, title_contains: str | None, limit: int
    ) -> list[WhatsAppChatRow]:
        parameters = {"title": title_contains, "limit": limit}
        with self._database.connect() as connection:
            rows = connection.execute(LIST_SQL, parameters).fetchall()
        return [WhatsAppChatRow(**dict(row)) for row in rows]
