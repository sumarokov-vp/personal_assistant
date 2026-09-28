import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from src.whatsapp.macos_desktop.services.core_data_clock.core_data_clock import (
    CORE_DATA_EPOCH,
)

SCHEMA = """
CREATE TABLE ZWACHATSESSION (
    Z_PK INTEGER PRIMARY KEY, Z_ENT INTEGER, ZSESSIONTYPE INTEGER,
    ZLASTMESSAGEDATE TIMESTAMP, ZCONTACTJID VARCHAR, ZPARTNERNAME VARCHAR
);
CREATE TABLE ZWAGROUPMEMBER (
    Z_PK INTEGER PRIMARY KEY, ZCHATSESSION INTEGER, ZCONTACTNAME VARCHAR,
    ZFIRSTNAME VARCHAR, ZMEMBERJID VARCHAR
);
CREATE TABLE ZWAMEDIAITEM (
    Z_PK INTEGER PRIMARY KEY, ZFILESIZE INTEGER, ZMESSAGE INTEGER,
    ZMEDIALOCALPATH VARCHAR, ZMEDIAURL VARCHAR, ZTITLE VARCHAR, ZMEDIAKEY BLOB
);
CREATE TABLE ZWAMESSAGE (
    Z_PK INTEGER PRIMARY KEY, ZISFROMME INTEGER, ZMESSAGETYPE INTEGER,
    ZCHATSESSION INTEGER, ZGROUPMEMBER INTEGER, ZMEDIAITEM INTEGER,
    ZMESSAGEDATE TIMESTAMP, ZFROMJID VARCHAR, ZPUSHNAME VARCHAR, ZTEXT VARCHAR,
    ZTOJID VARCHAR
);
"""

PERSONAL = 0
GROUP = 1


def core_data_seconds(moment: datetime) -> float:
    return (moment - CORE_DATA_EPOCH).total_seconds()


class SyntheticSnapshot:
    def __init__(self, snapshot_dir: Path) -> None:
        self.snapshot_dir = snapshot_dir
        self.database_path = snapshot_dir / "ChatStorage.sqlite"
        self.media_root = snapshot_dir / "Message"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.executescript(SCHEMA)
        self._next_pk = 1

    def chat(self, title: str | None, jid: str, session_type: int = PERSONAL) -> int:
        pk = self._pk()
        self._execute(
            "INSERT INTO ZWACHATSESSION (Z_PK, ZSESSIONTYPE, ZCONTACTJID, ZPARTNERNAME) "
            "VALUES (?, ?, ?, ?)",
            (pk, session_type, jid, title),
        )
        return pk

    def member(self, chat_pk: int, name: str, jid: str) -> int:
        pk = self._pk()
        self._execute(
            "INSERT INTO ZWAGROUPMEMBER (Z_PK, ZCHATSESSION, ZCONTACTNAME, ZMEMBERJID) "
            "VALUES (?, ?, ?, ?)",
            (pk, chat_pk, name, jid),
        )
        return pk

    def message(
        self,
        chat_pk: int,
        at: datetime,
        text: str | None,
        from_me: bool = False,
        member_pk: int | None = None,
        push_name: str | None = None,
        message_type: int = 0,
        media_pk: int | None = None,
    ) -> int:
        pk = self._pk()
        seconds = core_data_seconds(at)
        self._execute(
            "INSERT INTO ZWAMESSAGE (Z_PK, ZISFROMME, ZMESSAGETYPE, ZCHATSESSION, "
            "ZGROUPMEMBER, ZMEDIAITEM, ZMESSAGEDATE, ZPUSHNAME, ZTEXT) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                pk,
                int(from_me),
                message_type,
                chat_pk,
                member_pk,
                media_pk,
                seconds,
                push_name,
                text,
            ),
        )
        self._execute(
            "UPDATE ZWACHATSESSION SET ZLASTMESSAGEDATE = MAX(COALESCE(ZLASTMESSAGEDATE, 0), ?) "
            "WHERE Z_PK = ?",
            (seconds, chat_pk),
        )
        return pk

    def media(
        self,
        size: int,
        title: str | None = None,
        local_path: str | None = None,
        content: bytes | None = None,
    ) -> int:
        pk = self._pk()
        self._execute(
            "INSERT INTO ZWAMEDIAITEM (Z_PK, ZFILESIZE, ZMEDIALOCALPATH, ZTITLE) "
            "VALUES (?, ?, ?, ?)",
            (pk, size, local_path, title),
        )
        if local_path is not None and content is not None:
            file_path = self.media_root / local_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)
        return pk

    def mark_captured(self, stamp: str) -> None:
        (self.snapshot_dir / "snapshot_at").write_text(stamp + "\n", encoding="utf-8")

    def _execute(self, sql: str, parameters: tuple[object, ...]) -> None:
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.execute(sql, parameters)

    def _pk(self) -> int:
        pk = self._next_pk
        self._next_pk += 1
        return pk
