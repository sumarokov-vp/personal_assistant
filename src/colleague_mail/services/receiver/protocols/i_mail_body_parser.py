from typing import Protocol

from src.colleague_mail.services.entities.mail_body import MailBody


class IMailBodyParser(Protocol):
    def parse(self, raw: bytes) -> MailBody | None: ...
