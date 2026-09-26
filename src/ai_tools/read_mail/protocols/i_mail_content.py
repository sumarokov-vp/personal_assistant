from collections.abc import Sequence
from typing import Protocol

from src.ai_tools.read_mail.protocols.i_mail_attachment import IMailAttachment


class IMailContent(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def thread_id(self) -> str: ...

    @property
    def sender(self) -> str: ...

    @property
    def recipients(self) -> str: ...

    @property
    def subject(self) -> str: ...

    @property
    def date(self) -> str: ...

    @property
    def body(self) -> str: ...

    @property
    def attachments(self) -> Sequence[IMailAttachment]: ...
