import sqlite3

from src.whatsapp.macos_desktop.errors.whatsapp_schema_error import WhatsAppSchemaError

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "ZWAMESSAGE": (
        "Z_PK",
        "ZCHATSESSION",
        "ZGROUPMEMBER",
        "ZMEDIAITEM",
        "ZMESSAGEDATE",
        "ZMESSAGETYPE",
        "ZISFROMME",
        "ZFROMJID",
        "ZPUSHNAME",
        "ZTEXT",
    ),
    "ZWACHATSESSION": (
        "Z_PK",
        "ZPARTNERNAME",
        "ZCONTACTJID",
        "ZSESSIONTYPE",
        "ZLASTMESSAGEDATE",
    ),
    "ZWAGROUPMEMBER": ("Z_PK", "ZCONTACTNAME", "ZFIRSTNAME", "ZMEMBERJID"),
    "ZWAMEDIAITEM": ("Z_PK", "ZTITLE", "ZFILESIZE", "ZMEDIALOCALPATH"),
}


class SnapshotSchema:
    def verify(self, connection: sqlite3.Connection) -> None:
        for table, columns in REQUIRED_COLUMNS.items():
            present = {
                row[1]
                for row in connection.execute(
                    "SELECT * FROM pragma_table_info(?)", (table,)
                )
            }
            missing = [column for column in columns if column not in present]
            if not present:
                raise WhatsAppSchemaError(table, [])
            if missing:
                raise WhatsAppSchemaError(table, missing)
