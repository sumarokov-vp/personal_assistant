import imaplib
import ssl
from types import TracebackType
from typing import Self

from src.knowledge_intake.errors.imap_command_error import ImapCommandError
from src.knowledge_intake.models.imap_settings import ImapSettings
from src.knowledge_intake.models.mailbox_folder import MailboxFolder
from src.knowledge_intake.models.raw_letter import RawLetter

OK = "OK"


class ImapMailbox:
    def __init__(self, settings: ImapSettings) -> None:
        self._settings = settings
        self._connection: imaplib.IMAP4_SSL | None = None

    def __enter__(self) -> Self:
        connection = imaplib.IMAP4_SSL(
            self._settings.host,
            self._settings.port,
            ssl_context=ssl.create_default_context(),
            timeout=self._settings.timeout_seconds,
        )
        connection.login(self._settings.user, self._settings.password)
        self._connection = connection
        for folder in MailboxFolder:
            connection.create(folder.value)
        self._expect("SELECT", connection.select(self._settings.inbox)[0])
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        connection = self._open()
        self._connection = None
        connection.logout()

    def unread(self) -> list[RawLetter]:
        connection = self._open()
        status, data = connection.uid("SEARCH", "UNSEEN")
        self._expect("SEARCH", status)
        uids = data[0].split() if data and data[0] else []
        return [self._fetch(uid.decode("ascii")) for uid in uids]

    def move(self, uid: str, folder: MailboxFolder) -> None:
        connection = self._open()
        self._expect("STORE", connection.uid("STORE", uid, "+FLAGS", "(\\Seen)")[0])
        self._expect("MOVE", connection.uid("MOVE", uid, folder.value)[0])

    def _fetch(self, uid: str) -> RawLetter:
        status, data = self._open().uid("FETCH", uid, "(BODY.PEEK[])")
        self._expect("FETCH", status)
        content = next(
            (part[1] for part in data if isinstance(part, tuple) and len(part) > 1),
            b"",
        )
        return RawLetter(uid=uid, content=bytes(content))

    def _open(self) -> imaplib.IMAP4_SSL:
        if self._connection is None:
            raise ImapCommandError("connection", "ящик не открыт")
        return self._connection

    def _expect(self, command: str, status: str) -> None:
        if status != OK:
            raise ImapCommandError(command, status)
