from typing import Protocol

from src.ai_tools.read_mail.protocols.i_mail_content import IMailContent


class IMailReader(Protocol):
    def get_message(self, message_id: str) -> IMailContent: ...
