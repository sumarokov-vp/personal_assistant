import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from src.whatsapp.macos_desktop.errors.whatsapp_snapshot_missing_error import (
    WhatsAppSnapshotMissingError,
)
from src.whatsapp.macos_desktop.repos.snapshot_schema import SnapshotSchema

VISIBLE_MESSAGE_VIEW = """
CREATE TEMP VIEW visible_message AS
SELECT
    m.Z_PK AS message_pk,
    m.ZCHATSESSION AS chat_pk,
    c.ZPARTNERNAME AS chat_title,
    c.ZCONTACTJID AS chat_jid,
    c.ZSESSIONTYPE AS session_type,
    COALESCE(m.ZISFROMME, 0) AS from_me,
    m.ZPUSHNAME AS push_name,
    g.ZCONTACTNAME AS member_name,
    g.ZFIRSTNAME AS member_first_name,
    COALESCE(g.ZMEMBERJID, m.ZFROMJID) AS sender_jid,
    m.ZMESSAGEDATE AS sent_at,
    m.ZMESSAGETYPE AS message_type,
    CASE
        WHEN COALESCE(m.ZTEXT, '') <> '' THEN m.ZTEXT
        WHEN COALESCE(i.ZFILESIZE, 0) > 0 OR COALESCE(i.ZMEDIALOCALPATH, '') <> ''
            THEN COALESCE(i.ZTITLE, '')
        ELSE ''
    END AS body,
    (COALESCE(i.ZFILESIZE, 0) > 0 OR COALESCE(i.ZMEDIALOCALPATH, '') <> '')
        AS has_attachment,
    i.Z_PK AS media_pk,
    i.ZTITLE AS media_title,
    i.ZFILESIZE AS media_size,
    i.ZMEDIALOCALPATH AS media_path
FROM ZWAMESSAGE m
JOIN ZWACHATSESSION c ON c.Z_PK = m.ZCHATSESSION
LEFT JOIN ZWAGROUPMEMBER g ON g.Z_PK = m.ZGROUPMEMBER
LEFT JOIN ZWAMEDIAITEM i ON i.Z_PK = m.ZMEDIAITEM
WHERE COALESCE(m.ZTEXT, '') <> ''
   OR COALESCE(i.ZFILESIZE, 0) > 0
   OR COALESCE(i.ZMEDIALOCALPATH, '') <> ''
"""


def contains_casefolded(haystack: str | None, needle: str) -> bool:
    return haystack is not None and needle.casefold() in haystack.casefold()


class SnapshotDatabase:
    def __init__(self, database_path: Path, schema: SnapshotSchema) -> None:
        self._database_path = database_path
        self._schema = schema

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        if not self._database_path.is_file():
            raise WhatsAppSnapshotMissingError(self._database_path)
        uri = f"{self._database_path.resolve().as_uri()}?mode=ro&immutable=1"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            self._schema.verify(connection)
            connection.create_function(
                "contains_ci", 2, contains_casefolded, deterministic=True
            )
            connection.execute(VISIBLE_MESSAGE_VIEW)
            yield connection
